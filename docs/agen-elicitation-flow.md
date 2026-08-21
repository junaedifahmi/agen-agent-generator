Agen loops through one question at a time until everything's gathered, then asks a human to confirm before it generates anything.

```mermaid
flowchart TD
    start(["Start"]) --> loop["Agen asks one question at a time,\nrecords each answer"]
    loop --> check{"Everything\ngathered?"}
    check -- no --> loop

    check -- yes --> ask["Agen asks:\n'generate now?'"]
    ask --> confirm{"User\nconfirms?"}
    confirm -- no, more to add --> loop

    confirm -- yes --> generate["Generate chatbot:\nvalidate spec, export YAML,\nrun the generator"]:::gate
    generate --> fin(["End"])

    classDef gate fill:#fdf3e7,stroke:#a8631d,color:#7a4a15,stroke-width:2px;
```

The amber step only runs after an explicit human yes — nothing generates on Agen's own judgment.
