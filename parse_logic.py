import re


def parse_production_card(content):
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    result = {}

    # Simple fields
    simple_fields = [
        ("WO No.", r"^WO No\.?\s*(.+)$"),
        ("Sales Order", r"^Sales Order\s*(.+)$"),
        ("Run No.", r"^Run No\.?\s*(.+)$"),
        ("Serial No.", r"^Serial No\.?\s*(.+)$"),
        ("Model", r"^Model\s*(.+)$"),
        ("DC", r"^DC\s*(.+)$"),
        ("Dealer", r"^Dealer\s*(.+)$"),
        ("State", r"^State\s*(.+)$"),
        ("Decor", r"^Decor\s*(.+)$"),
        ("Color", r"^COVENTRY/WINTER FOG GLZ$"),
        ("Fin", r"^Fin\s*(.+)$"),
    ]
    for key, regex in simple_fields:
        for line in lines:
            match = re.match(regex, line)
            if match:
                result[key] = match.group(1) if match.lastindex else match.group(0)
                break

    # Chassis options
    chassis_start = next((i for i, line in enumerate(lines) if line.startswith("Chassis:")), -1)
    if chassis_start != -1:
        chassis = {}
        for j in range(chassis_start + 1, len(lines)):
            line = lines[j]
            if re.match(r"^[A-Z ]+$", line) or line.startswith("BIM CORRECT"):
                break
            match = re.match(r"^(\d+)\s+(.+)$", line)
            if match:
                chassis[match.group(1)] = match.group(2)
        result["Chassis"] = chassis

    # BIM
    bim_line = next((line for line in lines if line.startswith("BIM")), None)
    if bim_line:
        result["BIM"] = bim_line.replace("BIM", "").strip()

    # Comments
    comments_start = next((i for i, line in enumerate(lines) if line == "COMMENTS"), -1)
    if comments_start != -1:
        comments = []
        for j in range(comments_start + 1, len(lines)):
            if lines[j].startswith("FINAL ACCEPTANCE"):
                break
            comments.append(lines[j])
        result["Comments"] = [c for c in comments if c]

    # Final Acceptance
    final_start = next((i for i, line in enumerate(lines) if line.startswith("FINAL ACCEPTANCE")), -1)
    if final_start != -1:
        final = {}
        for j in range(final_start + 1, len(lines)):
            if lines[j].startswith('L:'):
                break
            if lines[j] == "Production Manager":
                final["Production Manager"] = lines[j+1]
            if lines[j].startswith("Date") and "Date" not in final:
                final["Date"] = lines[j].replace("Date", "").strip()
            if lines[j] == "Quality Control":
                final["Quality Control"] = lines[j+1]
            if lines[j] == "Production Scheduler":
                final["Production Scheduler"] = lines[j+1]
            if lines[j].startswith("Date") and "Scheduler Date" not in final:
                final["Scheduler Date"] = lines[j].replace("Date", "").strip()
            if lines[j].startswith("Dat"):
                final["Final Date"] = lines[j].replace("Dat", "").strip()
        result["Final Acceptance"] = final

    # Components Table Parsing (robust version)
    def is_valid_serial(s):
        # Accepts serials with at least 6 digits or uppercase letters/numbers
        return bool(re.match(r"^[A-Z0-9\-]{6,}$", s.strip()))

    try:
        eq_idx = lines.index("Equipment")
        make_idx = lines.index("Make")
        model_idx = lines.index("Model")
        sn_idx = lines.index("Serial Number")
        table_start = min(eq_idx, make_idx, model_idx, sn_idx) + 4
    except ValueError:
        table_start = -1

    section_breaks = set([
        "Rework / Stock outs", "Interior", "Exterior", "Information", "Complete", "Initial"
    ])

    # Known equipment names for correct mapping
    known_equipment = [
        "Chassis", "Engine", "Tires 1", "Tires 2", "Tires 3", "Tires 4", "Tires 5", "Tires 6 1", "Tires 7", "Tires 8",
        "Defrost Unit", "Dash A/C", "LP Tank", "Generator", "Key (ignition)", "Ent Door", "Patio", "Patio legs",
        "D/S window", "D/S window lower", "D/S window upper", "R/S window lower", "SO/ cover D/S", "SO/ cover P/S", "SO/ cover rear", "RVIA Tag"
    ]

    components = []
    i = table_start
    while table_start != -1 and i < len(lines):
        if not lines[i] or lines[i] in section_breaks:
            break

        equipment = lines[i].strip() if i < len(lines) else ""
        make = lines[i+1].strip() if i+1 < len(lines) else ""
        # Model may span multiple lines until we hit a valid serial or next equipment
        model_lines = []
        j = i+2
        while j < len(lines):
            candidate = lines[j].strip()
            # If candidate is a valid serial number, break
            if is_valid_serial(candidate):
                break
            # If candidate is next equipment (starts with known equipment)
            if candidate in known_equipment:
                break
            # If candidate is a section break, break
            if candidate in section_breaks:
                break
            model_lines.append(candidate)
            j += 1
        model = " ".join(model_lines).strip()
        # Serial number is next line after model, if valid
        serial = ""
        if j < len(lines) and is_valid_serial(lines[j].strip()):
            serial = lines[j].strip()
            next_i = j+1
        else:
            next_i = j
        components.append({
            "Equipment": equipment,
            "Make": make,
            "Model": model,
            "SerialNumber": serial
        })
        i = next_i

    if components:
        result["Components"] = components

    return result