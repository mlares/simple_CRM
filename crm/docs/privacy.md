# Privacidad, auditoría y retención

El acceso a un paquete de privacidad requiere `AUDIT_VIEW` y alcance global.
El paquete reúne partes, contactos y supresión, leads, actividad, tareas,
lineage y metadata de exportaciones, pero no duplica cuerpos completos de
notas, payloads de archivos, credenciales o tokens.

La supresión se ejecuta sobre `ContactPoint.suppress()` y nunca se revierte
desde el flujo normal. Importaciones, merges, informes y exportaciones deben
respetar ese estado.

La retención es preview-first: una categoría activa define propósito y días,
una previsualización registra elegibilidad, un legal hold excluye el objetivo,
y la ejecución exige aprobación explícita. La ejecución conserva el registro y
no realiza borrado destructivo silencioso; los trabajos destructivos requieren
una política posterior y revisión autorizada.

Este es un CRM comercial. No se deben registrar pacientes, historias clínicas,
diagnósticos ni otros datos clínicos. El contenido sensible se reporta al
responsable de privacidad mediante el incidente correspondiente.
