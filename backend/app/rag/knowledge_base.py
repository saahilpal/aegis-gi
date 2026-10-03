from typing import List, Dict, Any

DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "DOC-PEG-01",
        "document_name": "AGA Clinical Practice Guideline: Split-Dose Polyethylene Glycol (PEG-3350) Bowel Prep",
        "section": "Section 1.1: Split-Dose Timing & Fluid Volume",
        "keywords": ["split-dose", "miralax", "peg", "polyethylene glycol", "gatorade", "timing", "schedule", "dose", "water", "hydration"],
        "content": (
            "Split-dose bowel preparation is the clinical standard of care for colonoscopy. "
            "Patients should take the first dose (2 liters or 1 container of MiraLAX 238g in 64 oz clear fluid) "
            "between 5:00 PM and 6:00 PM on the evening before the colonoscopy. "
            "The second dose (remaining 2 liters or second 64 oz fluid) must be consumed 4 to 5 hours prior "
            "to the scheduled procedure arrival time. All fluid consumption must be fully completed strictly "
            "4 hours before procedure arrival to prevent pulmonary aspiration under sedation. "
            "Drink 8 ounces of the solution every 10 to 15 minutes until finished."
        )
    },
    {
        "id": "DOC-DIET-02",
        "document_name": "Endoscopy Center Clinical Protocol: Pre-Procedure Dietary Guidelines",
        "section": "Section 2.1: Low-Fiber Phase & Clear Liquid Diet",
        "keywords": ["diet", "food", "eat", "liquid", "clear liquids", "jello", "gelatin", "broth", "red dye", "purple dye", "coffee", "seeds"],
        "content": (
            "Starting 3 days prior to colonoscopy, adhere to a low-fiber diet: avoid nuts, seeds, popcorn, raw fruit/vegetables, "
            "whole grain bread, and corn. "
            "On the day before the procedure, consume ONLY clear liquids starting at breakfast. "
            "Permitted clear liquids include: water, clear apple juice, white grape juice, strained chicken or beef broth, "
            "black coffee or tea (no milk, creamer, or dairy), and electrolyte drinks like Gatorade. "
            "CRITICAL: Avoid any fluids, popsicles, or gelatin containing RED or PURPLE dyes, as red/purple residue "
            "mimics active mucosal hemorrhage in the colon. Yellow and green gelatin/popsicles are acceptable."
        )
    },
    {
        "id": "DOC-MEDS-DIABETES-03",
        "document_name": "Clinical Practice Update: Diabetic Medication Management During Bowel Preparation",
        "section": "Section 3.2: Basal Insulin & Oral Hypoglycemic Agents",
        "keywords": ["diabetes", "insulin", "lantus", "basaglar", "metformin", "glp-1", "ozempic", "hypoglycemia", "blood sugar", "units"],
        "content": (
            "Because patients are on a strict clear liquid diet with reduced caloric intake, medication adjustments are mandatory "
            "to prevent severe hypoglycemia: "
            "1. Basal Long-Acting Insulin (e.g., Lantus, Glargine, Basaglar, Levemir): Reduce the usual evening dose by 50% "
            "on the night prior to the colonoscopy. Do NOT withhold 100% of basal insulin, as total omission carries risk of diabetic ketoacidosis. "
            "2. Short-Acting / Prandial Insulin: Hold all rapid-acting insulin while on clear liquids unless elevated blood glucose correction is needed. "
            "3. Oral Hypoglycemics (Metformin, Glipizide, Januvia): Hold starting the morning of the procedure day. "
            "4. Monitor blood glucose every 4 hours during the prep. If blood glucose drops below 70 mg/dL, drink 4 oz of clear apple juice or suck on hard clear candy."
        )
    },
    {
        "id": "DOC-MEDS-ANTICOAG-04",
        "document_name": "Consensus Guidelines: Periprocedural Management of Anticoagulants and Antiplatelets",
        "section": "Section 4.1: Direct Oral Anticoagulants (DOACs) & Antiplatelets",
        "keywords": ["eliquis", "apixaban", "xarelto", "rivaroxaban", "plavix", "clopidogrel", "aspirin", "blood thinner", "anticoagulant", "bleeding"],
        "content": (
            "Direct Oral Anticoagulants (DOACs) such as Eliquis (apixaban) and Xarelto (rivaroxaban) increase the risk of post-polypectomy bleeding. "
            "DOACs must be held for 48 hours prior to diagnostic or screening colonoscopy (last dose taken 2 days before the procedure day), "
            "provided renal function is normal and approved by the prescribing cardiologist. "
            "Antiplatelet therapy (Plavix, Brilinta) requires explicit physician clearance before interruption. "
            "Standard low-dose Aspirin (81mg daily) may generally be continued unless otherwise instructed by the endoscopist."
        )
    },
    {
        "id": "DOC-POLICY-RESCHED-05",
        "document_name": "Gastroenterology Associates Clinic Policies & Operational Standards",
        "section": "Section 5.3: Rescheduling, Cancellation, and Escort Requirements",
        "keywords": ["reschedule", "cancel", "policy", "escort", "ride", "driver", "sedation", "arrival", "fee", "hours"],
        "content": (
            "1. Cancellation & Rescheduling: We require at least 48 business hours advance notice for rescheduling or cancelling "
            "an endoscopy or colonoscopy. This allows our clinical team to reallocate the procedure room and staff. "
            "2. Mandatory Adult Escort: Because intravenous conscious sedation or MAC (Monitored Anesthesia Care with Propofol) "
            "is administered, all patients MUST have a responsible adult (age 18+) accompany them to check-in, remain in the building "
            "during the procedure, and drive them home. Rideshares (Uber, Lyft, taxi) alone are strictly prohibited by state medical regulations "
            "unless accompanied by an adult companion. If an escort is unavailable, the appointment must be rescheduled."
        )
    },
    {
        "id": "DOC-SAFETY-TRIAGE-06",
        "document_name": "GI Clinic Triage & Emergency Escalation Matrix",
        "section": "Section 6.1: Red-Flag Symptoms During Bowel Preparation",
        "keywords": ["emergency", "red flag", "bleeding", "severe pain", "shortness of breath", "fainting", "vomiting", "blood", "911", "chest pain"],
        "content": (
            "Any of the following symptoms during bowel preparation represent clinical red flags requiring immediate human escalation: "
            "- Large-volume rectal bleeding (bright red blood clots filling the toilet bowl, distinct from pinkish prep fluid) "
            "- Severe, intractable abdominal pain (score 8-10/10) that is continuous rather than cramping "
            "- Severe shortness of breath, stridor, or facial swelling suggesting allergic anaphylaxis "
            "- Syncope (loss of consciousness) or persistent lightheadedness unable to stand "
            "- Inability to retain any liquids with persistent vomiting lasting over 2 hours "
            "In case of suspected hemodynamic instability, syncope, or severe chest pain, instruct patient to call 911 immediately. "
            "Do not provide clinical reassurance or home diagnosis."
        )
    }
]
