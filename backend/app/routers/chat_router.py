import time
import json
import uuid
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Response, Query, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from ..models.chat import ChatRequest, ChatResponse
from ..ehr.ehr_service import ehr_service
from ..agent.graph import agent_workflow
from ..agent.llm import llm_client
from ..verifier.outcome_verifier import outcome_verifier
from ..db.database import get_db_session
from ..db.models import (
    Conversation as ConversationModel,
    Message as MessageModel,
    TraceStep as TraceStepModel,
    OutcomeVerification as OutcomeVerificationModel,
)
from ..security.auth import security_bearer, decode_access_token
from ..security.rate_limiter import enforce_rate_limit

router = APIRouter(prefix="/api/chat", tags=["Chat & Streaming"])

def get_optional_auth_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except Exception:
        return None

async def persist_chat_turn(
    conversation_id: str,
    patient_id: str,
    user_message: str,
    agent_response: str,
    citations: list,
    trace_steps: list,
    verification: any
):
    """Store conversation, messages, execution trace, and outcome verification in PostgreSQL/DB."""
    try:
        async with get_db_session() as session:
            conv = await session.get(ConversationModel, conversation_id)
            if not conv:
                conv = ConversationModel(id=conversation_id, patient_id=patient_id)
                session.add(conv)
                await session.flush()

            user_msg = MessageModel(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                citations=[]
            )
            session.add(user_msg)

            asst_msg_id = str(uuid.uuid4())
            asst_msg = MessageModel(
                id=asst_msg_id,
                conversation_id=conversation_id,
                role="assistant",
                content=agent_response,
                citations=[c.dict() if hasattr(c, "dict") else c for c in citations]
            )
            session.add(asst_msg)

            for st in trace_steps:
                st_dict = st.dict() if hasattr(st, "dict") else st
                trace_rec = TraceStepModel(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    message_id=asst_msg_id,
                    node_id=st_dict.get("node_id", "NODE"),
                    node_name=st_dict.get("node_name", "Node"),
                    status=st_dict.get("status", "COMPLETED"),
                    latency_ms=st_dict.get("latency_ms", 0.0),
                    input_summary=str(st_dict.get("input_summary", ""))[:400],
                    output_summary=str(st_dict.get("output_summary", ""))[:400]
                )
                session.add(trace_rec)

            if verification:
                v_dict = verification.dict() if hasattr(verification, "dict") else verification
                verif_rec = OutcomeVerificationModel(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    message_id=asst_msg_id,
                    classification=v_dict.get("classification", "UNKNOWN"),
                    expected_outcome=v_dict.get("expected_outcome", ""),
                    actual_outcome=v_dict.get("actual_outcome", ""),
                    reason=v_dict.get("reason", ""),
                    evidence=v_dict.get("evidence", []),
                    discrepancy_detected=v_dict.get("discrepancy_detected", False)
                )
                session.add(verif_rec)

            await session.commit()
    except Exception:
        pass


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    auth_claims: Optional[Dict[str, Any]] = Depends(get_optional_auth_claims)
):
    """
    Standard chat endpoint:
    Executes LangGraph workflow -> OutcomeVerifier -> Persists to DB -> Returns verified response.
    """
    enforce_rate_limit(request, max_requests=40, window_seconds=60, operation="chat")
    t0 = time.time()
    before_snap = await ehr_service.take_snapshot_async()

    # Scope identity if authenticated
    effective_patient_id = req.patient_id
    effective_user_role = req.user_role.value if hasattr(req.user_role, "value") else str(req.user_role)

    if auth_claims:
        role = auth_claims.get("role", "PATIENT").upper()
        effective_user_role = role
        if role == "PATIENT":
            user_pid = auth_claims.get("patient_id") or auth_claims.get("sub")
            if user_pid and req.patient_id != user_pid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: Authenticated patient cannot execute workflows for '{req.patient_id}'."
                )
            effective_patient_id = user_pid or effective_patient_id

    state = {
        "user_message": req.message,
        "patient_id": effective_patient_id,
        "user_role": effective_user_role,
        "force_tool_failure": req.force_tool_failure,
        "force_agent_hallucination": req.force_agent_hallucination,
        "trace_steps": []
    }

    try:
        output = await agent_workflow.ainvoke(state)
        agent_response = output.get("final_response", "")
        agent_claim = output.get("agent_claim")
        citations = output.get("citations", [])
        trace_steps = output.get("trace_steps", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")

    after_snap = await ehr_service.take_snapshot_async()

    # Independent Outcome Verification
    verification = outcome_verifier.verify(
        user_message=req.message,
        agent_response=agent_response,
        agent_claim=agent_claim,
        before_snapshot=before_snap,
        after_snapshot=after_snap
    )

    total_latency = round((time.time() - t0) * 1000, 2)
    conv_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"

    # Persist to database asynchronously
    await persist_chat_turn(
        conversation_id=conv_id,
        patient_id=effective_patient_id,
        user_message=req.message,
        agent_response=agent_response,
        citations=citations,
        trace_steps=trace_steps,
        verification=verification
    )

    return ChatResponse(
        conversation_id=conv_id,
        response_text=agent_response,
        citations=citations,
        claimed_action=agent_claim,
        outcome_verification=verification,
        trace_steps=trace_steps,
        ehr_snapshot=after_snap,
        total_latency_ms=total_latency
    )


@router.get("/stream")
async def chat_stream_endpoint(
    request: Request,
    message: str = Query(..., min_length=1, max_length=4000),
    patient_id: str = Query("P101", max_length=64),
    force_tool_failure: str = Query("", max_length=32),
    force_agent_hallucination: bool = Query(False),
    token: Optional[str] = Query(None)
):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Emits real-time execution node transitions, token chunks, live claims, and final outcome verification.
    """
    enforce_rate_limit(request, max_requests=40, window_seconds=60, operation="chat_stream")

    # Validate token if supplied
    effective_patient_id = patient_id
    effective_role = "PATIENT"
    if token:
        try:
            claims = decode_access_token(token)
            role = claims.get("role", "PATIENT").upper()
            effective_role = role
            if role == "PATIENT":
                user_pid = claims.get("patient_id") or claims.get("sub")
                if user_pid:
                    effective_patient_id = user_pid
        except Exception:
            pass

    async def event_generator() -> AsyncGenerator[str, None]:
        before_snap = await ehr_service.take_snapshot_async()
        t0 = time.time()

        yield f"event: status\ndata: {json.dumps({'message': 'Executing LangGraph clinical reasoning...', 'status': 'STARTING'})}\n\n"

        state = {
            "user_message": message,
            "patient_id": effective_patient_id,
            "user_role": effective_role,
            "force_tool_failure": force_tool_failure if force_tool_failure else None,
            "force_agent_hallucination": force_agent_hallucination,
            "trace_steps": []
        }

        try:
            # Run workflow
            output = await agent_workflow.ainvoke(state)
            trace_steps = output.get("trace_steps", [])
            agent_response = output.get("final_response", "")
            agent_claim = output.get("agent_claim")
            citations = output.get("citations", [])

            # Stream the traversed trace steps
            for step in trace_steps:
                yield f"event: trace_step\ndata: {json.dumps(step.dict(), default=str)}\n\n"

            # Stream LLM tokens
            if llm_client.api_key and "PREP" in state.get("request_category", ""):
                prompt = f"Patient asks: {message}\nContext: {output.get('retrieved_context', '')}\nProvide safe, verified GI prep guidance."
                for chunk in llm_client.generate_stream(prompt):
                    yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
            else:
                words = agent_response.split(" ")
                for i in range(0, len(words), 4):
                    chunk = " ".join(words[i:i+4]) + " "
                    yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"

            after_snap = await ehr_service.take_snapshot_async()

            # Independent Outcome Verification
            verification = outcome_verifier.verify(
                user_message=message,
                agent_response=agent_response,
                agent_claim=agent_claim,
                before_snapshot=before_snap,
                after_snapshot=after_snap
            )

            total_latency = round((time.time() - t0) * 1000, 2)
            conv_id = f"conv-{uuid.uuid4().hex[:8]}"

            await persist_chat_turn(
                conversation_id=conv_id,
                patient_id=effective_patient_id,
                user_message=message,
                agent_response=agent_response,
                citations=citations,
                trace_steps=trace_steps,
                verification=verification
            )

            yield f"event: outcome\ndata: {json.dumps(verification.dict(), default=str)}\n\n"
            yield f"event: ehr_diff\ndata: {json.dumps(ehr_service.diff_snapshot(before_snap, after_snap), default=str)}\n\n"
            final_payload = {
                "response_text": agent_response,
                "citations": [c.dict() for c in citations],
                "total_latency_ms": total_latency
            }
            yield f"event: done\ndata: {json.dumps(final_payload, default=str)}\n\n"
        except asyncio.CancelledError:
            # Client disconnected gracefully
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no"
        }
    )
