# Parked wedges (do not build yet)

Two-person team. The live product is still intake → taxonomía → GraphRAG and/or SQL → Reviewer → Courier. Harden and test that line first. These are **utilities on the same platform**, not a second SaaS. Translate before adding a node.

## Auditor (compliance / procedimientos)

- **Dolor:** 50–1000 empleados, 200 manuales / PRL / ISO / onboarding. Se trabaja de memoria. La auditoría interna tarda semanas.
- **Oficio:** Auditor (un trabajo: comparar un hecho con la normativa vigente y dejar un desvío). No es Librarian (Librarian responde; Auditor señala).
- **Ya existe:** Library + Taxonomist (Advice / Factory parked) → promote a GraphRAG → Pathfinder/Librarian recuperan. Reviewer aguanta excepciones. Courier avisa.
- **Falta:** tool `compliance.check`, arista en el grafo, corpus de *políticas vigentes* promovido a propósito (no dumpster de 200 PDFs).
- **Instancia / binding:** mismo oficio por cliente (árbol + `scope_path`). No clonar “Auditor ISO” vs “Auditor Asesoría”.
- **No construir:** Compliance GPT, ontología artesanal, otro RAG, 200 agentes PRL.

## Reconciler (ERP vs documentos)

- **Dolor:** ERP/CRM (SQL/SAP/Holded) y PDFs/albaranes/pedidos en el correo no cuadran. Horas de cruce a mano.
- **Oficio:** Reconciler (un trabajo: cruzar la fila extraída con el pedido del ERP). No es Extractor (Extractor escribe SQL; Reconciler compara).
- **Ya existe:** Parser/Reader → Extractor/Recorder (SQL) → Reviewer (facturas flojas) → Courier.
- **Falta:** credential binding (`erp:holded` o SQL) en la instancia, tool `records.reconcile`, descuadre explícito al Reviewer (“+5% no está en la OC #4501”).
- **Instancia / binding:** un ERP primero. Holded vs SAP es otro binding, no otro oficio.
- **No construir:** conector SAP/Holded/Sage como producto, Custodian de APIs, CRM.

When a founder picks one, add agent + tool + seed + graph edge. The other waits.
