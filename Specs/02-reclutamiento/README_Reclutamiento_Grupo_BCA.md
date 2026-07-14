# ÉPICA: Reclutamiento y Habilitación de Agentes
*Proyecto: Grupo BCA*

## 1. DESCRIPCIÓN Y OBJETIVO
> Transformar el proceso de reclutamiento y habilitación de agentes de Grupo BCA —hoy llevado en monday.com, con captura inconsistente y una conversión de apenas 3–4%— en un embudo ordenado y medible dentro de Odoo, que acompañe al candidato desde que se recibe o prospecta hasta que el agente tiene su **cédula emitida** y entra a Desarrollo Comercial. Incluye también los puestos internos (que se cierran como contratados sin pasar por cédula). El objetivo de negocio es devolverle a BCA control y visibilidad sobre su reclutamiento, para saber dónde se cae cada candidato, cuánto tarda el proceso y qué canal trae a los mejores prospectos, sin depender de Excel.

## 2. DEFINICIÓN DE HECHO (DoD)
*Para considerar este proyecto como "Completado", se deben cumplir los siguientes criterios:*
- [ ] BDD de reclutamiento revisado y **autorizado por el cliente** (Guillermo).
- [ ] SDD y plan de implementación por sprints elaborados a partir del BDD.
- [ ] Proceso configurado en Odoo: un candidato se lleva de **"Recibido" a "En Desarrollo Comercial"** sin salir del sistema, y cada estado/etapa se actualiza con un clic.
- [ ] Los **tres reportes** (embudo de conversión, tiempos del proceso, efectividad por fuente/campaña/evento) se generan solos, sin Excel.
- [ ] Histórico de monday.com **migrado** con catálogos limpios (sede, puesto, fuente, campaña, promotor).
- [ ] Reclutadoras **capacitadas**: una persona nueva entiende el flujo sin explicación técnica.

## 3. ESTRUCTURA DE LA ÉPICA
* **`SPECS/`**: Archivos de control y memoria viva (Bugs, Decisiones, Estrategia, Routemap).
* **`Archivos_Cliente/`**: Insumos crudos recibidos.
    * `Charla con Guillermo sobre reclutamiento.md` — necesidades iniciales del proceso.
    * `Pipeline_de_Recluta_1780692911.xlsx` — export de monday.com (1,851 candidatos + bitácora).
    * `Respuestas_Guillermo_pendientes.md` — aclaraciones del negocio (Autos, visto bueno, plazos, permisos).
* **`Entregas/`**: Artefactos finales.
    * `BDD-Reclutamiento-Agentes-Grupo-BCA-v1.3` (Word para autorización + Markdown para versionado).
    * *(Próximos)* SDD, plan de implementación, módulo personalizado, configuraciones exportadas y materiales de capacitación.

## 4. ESTADO ACTUAL
* **Sprint Activo:** Fase 0 — Diagnóstico y Estrategia (MIOR): cierre del BDD.
* **Enfoque Actual:** Autorización del **BDD v1.3** por parte de Guillermo y preparación de las decisiones de diseño para arrancar el SDD y el plan por sprints.
* **Bloqueos:**
    * Esperando la **autorización del BDD v1.3** por parte del cliente.
    * Pendiente de negocio por definir: **inversión por canal** (si se quiere medir el costo por contratación por fuente/campaña, o si por ahora basta con volumen y conversión).

## 5. INSTRUCCIONES PARA AGENTES DE IA
1. **Antes de operar:** Lee el `BDD-Reclutamiento-Agentes-Grupo-BCA` (fuente de verdad del comportamiento del negocio) y el archivo `SPECS/Estrategia.md` para entender el enfoque técnico. Toda implementación parte del BDD; el "cómo" técnico no debe contradecir el "qué" acordado ahí.
2. **Registro:** Cada decisión técnica relevante debe ser volcada en `SPECS/Decisiones.md`.
3. **Control:** Reporta cualquier error detectado en `SPECS/Bugs.md`.
4. **Sincronización:** Asegúrate de que los archivos de configuración nuevos estén guardados en la carpeta `Entregas/` del Sprint correspondiente.

---
*Este proyecto es parte del ecosistema de Habitat Digital.*
