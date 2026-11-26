"""Vérifie la structure des workflows n8n exportés.

Usage : python3 -I scripts/check_n8n.py workflows/*.json
Sort en code 1 s'il reste une ERREUR (connexion vers un nœud inexistant, nom en double,
typeVersion ou position manquant, secret en clair probable).
"""
import json, sys, re
def check(path):
    d = json.load(open(path, encoding="utf-8"))
    errs, warns = [], []
    for k in ("name", "nodes", "connections"):
        if k not in d: errs.append(f"clé manquante : {k}")
    nodes = d.get("nodes", [])
    names = [n.get("name") for n in nodes]
    if len(names) != len(set(names)): errs.append("noms de nœuds en double")
    known = set(names)
    for n in nodes:
        t = n.get("type", "")
        if not re.match(r"^(n8n-nodes-base|@n8n/n8n-nodes-langchain)\.[A-Za-z0-9]+$", t):
            warns.append(f"préfixe inconnu (nœud communautaire ou inventé ?) : {n.get('name')} -> {t}")
        if "typeVersion" not in n: errs.append(f"typeVersion manquant : {n.get('name')}")
        if "position" not in n: errs.append(f"position manquante : {n.get('name')}")
        blob = json.dumps(n.get("parameters", {}))
        if re.search(r"(sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9._-]{20,})", blob):
            errs.append(f"secret en clair probable dans : {n.get('name')}")
    targets = set()
    for src, outs in d.get("connections", {}).items():
        if src not in known: errs.append(f"connexion depuis un nœud inexistant : {src}")
        for ctype, branches in outs.items():
            for br in branches:
                for c in br or []:
                    if c.get("node") not in known: errs.append(f"connexion vers un nœud inexistant : {src} -> {c.get('node')}")
                    if c.get("type") != ctype: warns.append(f"type de connexion incohérent : {src} ({ctype} vs {c.get('type')})")
                    targets.add(c.get("node"))
    trig = re.compile(r"(Trigger|trigger|webhook|Webhook)")
    for n in nodes:
        nm = n["name"]
        if nm not in targets and nm not in d.get("connections", {}) and not trig.search(n["type"]):
            warns.append(f"nœud isolé : {nm}")
    types = sorted({n.get("type","") for n in nodes})
    return errs, warns, types
ok = True
for p in sys.argv[1:]:
    e, w, t = check(p)
    print(f"== {p} : {len(e)} erreur(s), {len(w)} avertissement(s)")
    for x in e: print("  ERREUR", x)
    for x in w: print("  avert.", x)
    print("  types à confirmer dans le dépôt n8n-io/n8n :", ", ".join(t))
    ok = ok and not e
sys.exit(0 if ok else 1)
