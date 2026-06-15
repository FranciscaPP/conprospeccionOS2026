# Conprospeccion OS Vision

Documento estrategico vivo para preservar la vision de producto, reglas de negocio, decisiones operativas, hipotesis, ideas futuras y decisiones abiertas de Conprospeccion OS.

Este documento no es una especificacion cerrada ni un backlog de implementacion inmediata. Su objetivo es evitar perdida de conocimiento antes de seguir desarrollando.

## Estado Del Documento

- Fecha de congelamiento inicial: 2026-06-06
- Cliente piloto operativo: GBS Logistics
- Identificador operativo normalizado propuesto: `gbs_logistics`
- Stack visual aprobado para producto principal: dashboards desplegados en Vercel, repo `FranciscaPP/conprospeccionOS2026`, Next.js app router, Tailwind/shadcn, componentes reutilizables del producto.
- Stack no aprobado para version final del producto principal: Streamlit. Puede existir como prototipo, auditoria o herramienta auxiliar, pero no como destino final de Client Setup OS.

## Taxonomia De Estado

Cada elemento estrategico debe marcarse con uno de estos estados:

- Decision aprobada: regla, direccion o restriccion ya confirmada.
- Hipotesis: idea razonable que requiere validacion operativa o de datos.
- Idea futura: oportunidad relevante sin compromiso de implementacion inmediata.
- Pendiente de definicion: decision necesaria antes de construir o automatizar.

## Vision General

Conprospeccion OS debe evolucionar hacia un sistema operativo comercial B2B que conecte setup de cliente, prospeccion, ejecucion SDR, validacion de reuniones, inteligencia de revenue y aprendizaje historico.

Flujo estrategico aprobado:

1. Onboarding
2. Client Setup OS
3. Apollo
4. Snov
5. GHL
6. SDR
7. Reuniones
8. Validacion
9. Revenue Intelligence

Decision aprobada: el portal cliente no debe contener la operacion real del setup. El portal cliente captura intake inicial, especialmente onboarding e ICP. La operacion interna vive en Client Setup OS.

Decision aprobada: GBS Logistics es el primer cliente piloto, pero el modelo debe escalar a Clickie, Bambu Tech, Tiresias, Just4U, iCredit y clientes futuros.

Decision aprobada: no se deben conectar APIs reales hasta aprobar la arquitectura, modelo de datos y experiencia de usuario.

Decision aprobada: Supabase debe ser la fuente de verdad futura para entidades normalizadas, pero no se conecta en esta fase visual.

## Principios De Producto

Decision aprobada: Conprospeccion no trabaja con ICP estatico. Trabaja con iteracion operativa.

Decision aprobada: cada cliente debe tener estados, historial, checklist, configuracion, segmentos, BBDD, campanas, SDR y resultados.

Decision aprobada: cada subsegmento debe poder tener BBDD propia, campanas propias, SDR propio, resultados propios, estado propio y aprendizaje propio.

Decision aprobada: la interfaz debe mantener el mismo nivel visual de los dashboards principales: Performance Overview, Meeting Validation y Revenue Intelligence.

Decision aprobada: no se debe construir una pantalla tecnica simple ni una tabla aislada para Client Setup OS.

Decision aprobada: el sistema debe separar claramente:

- Intake del cliente
- Setup interno
- Ejecucion de prospeccion
- Validacion de reuniones
- Analisis comercial
- Aprendizaje historico

## 1. Client Setup OS

### Decision aprobada

Client Setup OS sera el modulo interno principal de operaciones de Conprospeccion OS.

Debe vivir en el stack visual del producto principal desplegado en Vercel, no dentro del portal cliente y no como pantalla final en Streamlit.

Debe controlar el setup completo del cliente:

- Intake recibido
- Estado de revision
- Fecha de recepcion
- Responsable
- ICP y Target Market Profile
- Paises
- Industrias
- Cargos
- Tamano de empresa
- Keywords opcionales
- Empresas objetivo
- Empresas excluidas
- Dominios
- Correos
- Firmas
- Warmup
- Bases de datos
- Campanas
- Usuarios GHL
- SDR asignado
- Checklist de lanzamiento
- Historial y estados del setup

Decision aprobada: GBS Logistics es el piloto inicial.

Decision aprobada: el setup debe reutilizar informacion existente cuando sea posible, sin duplicar ICP, onboarding, bases, campanas, Snov, GHL o archivos historicos.

Decision aprobada: deben detectarse y marcarse riesgos como:

- Slugs distintos
- Firmas duplicadas
- Bases duplicadas
- Campanas duplicadas
- Configuraciones mezcladas
- Riesgos de configuracion GHL
- Campanas sin cliente
- Campanas sin segmento
- Campanas sin pais
- BBDD duplicada
- Campana antigua
- Mala nomenclatura
- BBDD incompleta

Decision aprobada: estados para campanas y BBDD existentes:

- Activa
- Pausada
- En revision
- Mala calidad
- Reutilizable
- Descartar
- Pendiente segmentar
- Pendiente cargar Snov
- Pendiente cargar GHL

### Hipotesis

Client Setup OS puede convertirse en el punto de control unico para aprobar el paso desde intake hacia ejecucion real.

El checklist de lanzamiento puede funcionar como gate operativo antes de activar Apollo, Snov, GHL y SDR.

El historial del setup puede convertirse en una fuente de aprendizaje para estimar tiempos, riesgos y capacidad.

### Ideas futuras

- Score de readiness por cliente.
- Alertas automaticas de configuracion incompleta.
- Timeline visual del setup.
- Comparacion entre setups de clientes similares.
- Recomendacion automatica de segmentos iniciales.
- Deteccion automatica de campanas antiguas o mal segmentadas.
- Auditoria automatica de nomenclatura.
- Estado de salud por cliente.
- Vista por responsable operativo.

### Pendientes de definicion

- Modelo final de permisos por rol.
- Alcance exacto de edicion manual antes de conectar Supabase.
- Que datos historicos de GBS se migran primero.
- Como resolver duplicados entre repositorios, carpetas historicas y fuentes externas.
- Criterio formal para descartar o reutilizar BBDD.
- Criterio formal para pausar segmentos.

## 2. Meeting Lifecycle Engine

### Decision aprobada

Las reuniones deben tener un ciclo de vida trazable desde agendamiento hasta resultado comercial.

El sistema ya maneja conceptos como:

- Estado de reunion
- Validacion Conprospeccion
- Validacion cliente
- Validez final
- Estado comercial
- BANT
- Comentarios internos
- Comentarios cliente
- Disputas
- Reuniones pendientes

Reglas existentes observadas en el producto:

- Si la validacion del cliente esta pendiente, la validez final permanece pendiente.
- Si Conprospeccion marca valida y el cliente marca no valida, la reunion entra en disputa.
- Si una reunion fue reagendada, el estado final debe reflejar reagendamiento.
- Si ambas validaciones son validas, la reunion puede ser valida final.
- Si Conprospeccion marca no valida, la reunion puede terminar como no valida final.
- Si cliente y Conprospeccion coinciden en no valida, queda no valida final.

### Hipotesis

Meeting Lifecycle Engine debe transformarse en una capa central reutilizable por portal cliente, operaciones internas, Revenue Intelligence y pagos SDR.

La validez final deberia alimentar directamente el cumplimiento contractual y la medicion de revenue.

### Ideas futuras

- Auditoria de reuniones por motivo de invalidez.
- Deteccion de reuniones en disputa con SLA.
- Reglas configurables por cliente.
- Calculo automatico de validez proyectada.
- Analisis de calidad por SDR, campana, segmento y fuente.

### Pendientes de definicion

- SLA formal para validacion cliente.
- SLA formal para resolucion de disputas.
- Quien puede modificar validez final.
- Como versionar cambios de validacion.
- Como se conecta validacion con facturacion o pago variable.

## 3. SDR Portal

### Decision aprobada

Debe existir una experiencia para SDR orientada a ejecucion y seguimiento.

El SDR debe poder operar con:

- Cliente asignado
- Segmento asignado
- Campanas activas
- Reuniones agendadas
- Estados de seguimiento
- Resultados comerciales
- Indicadores de actividad

### Hipotesis

El SDR Portal puede reducir friccion si muestra prioridades diarias en vez de solo reportes historicos.

La asignacion de SDR por segmento, no solo por cliente, puede mejorar foco operativo y aprendizaje.

### Ideas futuras

- Ranking SDR.
- Cola de tareas diaria.
- Alertas de seguimiento.
- Objetivos por semana.
- Control de actividad por canal.
- Vista de pipeline personal.
- Recomendaciones de mejores horarios para contacto.

### Pendientes de definicion

- Que acciones podra ejecutar el SDR dentro del sistema.
- Si el SDR usara GHL como sistema principal o Conprospeccion OS como capa superior.
- Nivel de visibilidad del SDR sobre resultados de otros SDR.
- Modelo de incentivos y pago variable.

## 4. SDR Intelligence

### Decision aprobada

El sistema debe medir performance SDR mas alla de cantidad de reuniones.

Debe analizar:

- Llamadas
- Emails
- WhatsApp
- LinkedIn
- Reuniones agendadas
- Reuniones completadas
- Reuniones validas
- Conversacion a cliente ganado
- Actividad diaria
- Performance por cliente
- Performance por campana

### Hipotesis

La inteligencia SDR debe permitir identificar patrones replicables entre mejores SDR.

La calidad de reuniones debe pesar mas que el volumen bruto.

### Ideas futuras

- Ranking SDR ponderado por calidad.
- Ranking SDR por cliente.
- Ranking SDR por segmento.
- Ranking SDR por canal.
- Analisis por horario.
- Analisis por dia de la semana.
- Analisis por pais.
- Analisis por industria.
- Analisis por cargo.
- Analisis por tamano de empresa.
- Prediccion de capacidad de agendamiento.
- Recomendaciones automaticas de foco diario.

### Pendientes de definicion

- Formula oficial de ranking.
- Peso de reunion valida vs reunion agendada.
- Peso de cliente ganado.
- Peso de actividad vs resultado.
- Como evitar incentivos incorrectos.

## 5. Prospecting Intelligence Engine

### Decision aprobada

Conprospeccion OS debe aprender que prospectos, segmentos, paises, industrias, cargos y mensajes funcionan mejor.

Debe conectar el setup con ejecucion y resultados.

### Hipotesis

El motor de inteligencia de prospeccion puede recomendar donde invertir capacidad SDR y donde pausar esfuerzo.

La calidad de BBDD puede predecirse antes de lanzar campanas si se auditan atributos como dominio, cargo, pais, industria y duplicados.

### Ideas futuras

- Scoring de prospectos.
- Scoring de empresas.
- Scoring de segmentos.
- Priorizacion automatica de bases.
- Deteccion de bases malas antes de cargar a Snov o GHL.
- Recomendaciones de pais e industria por cliente.
- Benchmark entre clientes similares.
- Identificacion de segmentos parecidos a los ganadores.
- Deteccion de saturacion de mercados.

### Pendientes de definicion

- Variables minimas para scoring.
- Si el scoring sera manual, estadistico o IA.
- Umbral para pausar o descartar segmentos.
- Relacion entre scoring y asignacion de SDR.

## 6. Revenue Intelligence

### Decision aprobada

Revenue Intelligence debe mostrar lectura ejecutiva, embudo, segmentos, hallazgos, recomendaciones y campanas.

Debe conectar actividad comercial con resultados:

- Contactos trabajados
- Empresas impactadas
- Respuestas
- Respuestas positivas
- Reuniones agendadas
- Reuniones validas
- Meta contractual
- Avance de meta
- Segmentos con mejor senal
- Riesgos operativos
- Proximas decisiones

### Hipotesis

Revenue Intelligence debe ser el modulo que traduce operacion en decisiones comerciales para cliente y direccion interna.

La metrica central no debe ser solo cantidad de reuniones, sino aprendizaje accionable y revenue potencial.

### Ideas futuras

- Recomendaciones automaticas de reasignacion de capacidad.
- Prediccion de cumplimiento de meta contractual.
- Forecast de reuniones validas.
- Forecast de pipeline.
- Benchmark con clientes similares.
- Identificacion de oportunidades de upsell.
- Analisis de campanas ganadoras.
- Deteccion de cuellos de botella por etapa.

### Pendientes de definicion

- Formula oficial de revenue score.
- Como conectar revenue real o pipeline real.
- Que datos vera el cliente vs operaciones internas.
- Periodicidad del reporte ejecutivo.

## 7. ICP Engine

### Decision aprobada

El ICP no debe ser fijo. Debe soportar Target Market Profile principal y subsegmentos.

Ejemplos de subsegmentos:

- Chile / Mineria / Comercio Exterior
- Chile / Tecnologia / Supply Chain
- Peru / Retail / Operaciones
- Mexico / Manufactura / Compras
- Colombia / Equipamiento Medico / Abastecimiento
- Centroamerica / Repuestos / Dueno

Cada subsegmento debe poder tener:

- BBDD propia
- Campanas propias
- SDR propio
- Resultados propios
- Estado propio
- Aprendizaje u observaciones

Decision aprobada: Client Setup OS debe permitir editar, agregar, crear nuevos segmentos, crear nuevas BBDD, pausar segmentos y descartar segmentos, aunque el onboarding original diga otra cosa.

### Hipotesis

El ICP Engine puede convertirse en el centro de aprendizaje historico del negocio.

Los segmentos deben evolucionar segun resultados, no solo segun definicion inicial del cliente.

### Ideas futuras

- Versionado de ICP.
- Historial de cambios de segmentos.
- Comparacion de segmentos.
- Recomendacion automatica de nuevos subsegmentos.
- Deteccion de segmentos con baja calidad.
- Libreria de ICP por industria.

### Pendientes de definicion

- Campos obligatorios del ICP.
- Como versionar cambios.
- Quien aprueba cambios de ICP.
- Como se refleja un cambio de ICP en campanas activas.

## 8. Campaign Intelligence

### Decision aprobada

Las campanas existentes no deben borrarse sin auditoria. Deben clasificarse.

Cada campana debe mostrar:

- Nombre
- Cliente
- Fuente
- Segmento
- Prospectos
- Estado
- Calidad estimada
- Observaciones

Estados aprobados para clasificacion:

- Activa
- Pausada
- En revision
- Mala calidad
- Reutilizable
- Descartar
- Pendiente segmentar
- Pendiente cargar Snov
- Pendiente cargar GHL

### Hipotesis

Campaign Intelligence puede detectar por que una campana funciona o falla, combinando segmento, mensaje, canal, base y SDR.

### Ideas futuras

- Score de calidad de campana.
- Deteccion de mala nomenclatura.
- Deteccion de campanas antiguas.
- Analisis de conversion por secuencia.
- Recomendacion de asunto y CTA.
- Reutilizacion de campanas ganadoras en clientes similares.
- Auditoria de duplicados entre Snov y GHL.

### Pendientes de definicion

- Criterio oficial de calidad estimada.
- Umbral de campana mala.
- Politica de archivo vs descarte.
- Convencion de nombres.

## 9. Account Intelligence

### Decision aprobada

El sistema debe diferenciar empresas objetivo y empresas excluidas.

Tipos de exclusiones:

- Clientes actuales
- Clientes historicos
- Competidores
- Exclusiones especificas del cliente

### Hipotesis

Account Intelligence puede evitar dano comercial bloqueando cuentas sensibles antes de cargarlas a campanas.

Puede tambien identificar cuentas de alto valor para tratamiento especial.

### Ideas futuras

- Account scoring.
- Deteccion automatica de dominio duplicado.
- Deteccion de conflicto entre cliente objetivo y cliente excluido.
- Priorizacion de cuentas target.
- Enriquecimiento automatico de cuenta.
- Relacion entre account fit y resultados.

### Pendientes de definicion

- Campos obligatorios de cuenta.
- Reglas de bloqueo.
- Quien puede desbloquear una cuenta.
- Como sincronizar exclusiones con Apollo, Snov y GHL.

## 10. Capacity Planner

### Decision aprobada

La capacidad SDR debe relacionarse con clientes, segmentos, campanas y metas.

### Hipotesis

Un Capacity Planner puede anticipar si Conprospeccion tiene capacidad suficiente para cumplir metas por cliente.

La capacidad debe planificarse por cliente y por segmento, no solo por SDR.

### Ideas futuras

- Planificador de capacidad semanal.
- Forecast de reuniones agendadas.
- Forecast de reuniones validas.
- Deteccion de sobrecarga SDR.
- Recomendacion de reasignacion.
- Simulacion de escenarios.
- Capacidad por pais, industria y campana.
- SLA de seguimiento por etapa.

### Pendientes de definicion

- Unidad base de capacidad: horas, llamadas, contactos, campanas o reuniones.
- Modelo de productividad SDR.
- Relacion entre capacidad y meta contractual.
- Como considerar curva de aprendizaje de nuevos SDR.

## 11. Integracion Apollo

### Decision aprobada

Apollo sera una fuente futura para busqueda y carga de BBDD, pero no debe conectarse todavia en Client Setup OS.

### Hipotesis

Apollo puede alimentar empresas objetivo, contactos y enriquecimiento inicial de segmentos.

### Ideas futuras

- Busqueda desde segmentos ICP.
- Importacion controlada de cuentas.
- Validacion de duplicados antes de cargar.
- Enriquecimiento de dominios.
- Score de fit antes de exportar.

### Pendientes de definicion

- Campos minimos para importar.
- Politica de deduplicacion.
- Sincronizacion con Supabase.
- Limites de uso y costos.
- Flujo de aprobacion antes de cargar a Snov o GHL.

## 12. Integracion Snov

### Decision aprobada

Snov sera parte del flujo futuro para warmup, carga de BBDD y creacion de campanas, pero no debe conectarse todavia.

### Hipotesis

Snov puede funcionar como capa principal de outbound email y warmup.

### Ideas futuras

- Estado de warmup por casilla.
- Carga segmentada de BBDD.
- Creacion de campanas desde Client Setup OS.
- Auditoria de campanas Snov existentes.
- Alertas de campanas mal segmentadas.

### Pendientes de definicion

- Que entidad es fuente de verdad para campanas: Supabase o Snov.
- Como mapear campanas existentes.
- Como tratar contactos duplicados.
- Como separar campanas por subsegmento.

## 13. Integracion GHL

### Decision aprobada

GHL debe contemplar creacion/asignacion de usuarios, cliente asociado y seguimiento comercial futuro, pero no se conecta todavia.

### Hipotesis

GHL puede operar como CRM de ejecucion mientras Conprospeccion OS funciona como capa de inteligencia y control.

### Ideas futuras

- Creacion/asignacion de usuarios GHL.
- Auditoria de configuraciones mezcladas.
- Sincronizacion de contactos y oportunidades.
- Seguimiento de pipeline.
- Validacion de riesgos de configuracion antes de lanzar.

### Pendientes de definicion

- Fuente de verdad para usuarios.
- Relacion entre usuario GHL y SDR.
- Estructura de pipelines por cliente.
- Reglas de permisos.
- Como evitar mezcla de configuraciones entre clientes.

## 14. Integracion Hostinger

### Decision aprobada

Hostinger debe considerarse para compra/configuracion de dominios dentro del setup, pero no se conecta todavia.

### Hipotesis

La gestion de dominios puede estandarizarse como paso del checklist de lanzamiento.

### Ideas futuras

- Registro de dominio.
- Estado DNS.
- Estado de creacion.
- Fecha de compra.
- Proveedor.
- Alertas de renovacion.
- Checklist SPF, DKIM, DMARC.

### Pendientes de definicion

- Si Hostinger sera proveedor unico o uno de varios.
- Proceso de compra aprobado.
- Quien aprueba dominios.
- Convencion de nombres de dominio.

## 15. Integracion Zapmail

### Decision aprobada

Zapmail u otro proveedor debe contemplarse para compra o creacion de correos, pero no se conecta todavia.

### Hipotesis

La creacion de correos debe vincularse a dominio, firma, warmup, campana y SDR.

### Ideas futuras

- Creacion automatica de casillas.
- Estado de casilla.
- Asignacion por segmento.
- Firma asociada.
- Estado de warmup.
- Rotacion de casillas.
- Alertas de reputacion.

### Pendientes de definicion

- Proveedor final.
- Naming convention de casillas.
- Numero de casillas por cliente o segmento.
- Reglas de rotacion.
- Relacion con Snov warmup.

## Modelo De Datos Propuesto

Decision aprobada como propuesta, no migracion aplicada:

- `client_setup`
- `client_setup_steps`
- `client_icp_profiles`
- `client_icp_segments`
- `client_target_accounts`
- `client_excluded_accounts`
- `client_domains`
- `client_mailboxes`
- `client_email_signatures`
- `client_warmup`
- `client_databases`
- `client_campaigns`
- `client_sdr_assignments`
- `client_setup_history`

Pendiente de definicion:

- Relacion final con tablas existentes.
- Politica de RLS.
- Migracion de historicos.
- Campos obligatorios.
- Versionado de entidades.
- Auditoria de cambios.

## Reglas De Negocio Definidas Hasta Ahora

### Onboarding

- El portal cliente captura onboarding e ICP inicial.
- El portal cliente no gestiona setup real.
- El onboarding alimenta Client Setup OS.
- Client Setup OS puede modificar, ampliar o descartar informacion del onboarding.

### Setup

- Todo cliente debe tener checklist de lanzamiento.
- Todo cliente debe tener historial de acciones.
- Todo setup debe tener responsable.
- GBS Logistics es piloto.
- `gbs_logistics` es identificador operativo propuesto.
- No se debe duplicar informacion existente si puede normalizarse.

### ICP

- ICP no es fijo.
- El Target Market Profile principal puede tener multiples subsegmentos.
- Cada subsegmento puede tener estado, BBDD, campana, SDR, resultados y aprendizaje.
- Un segmento puede pausarse o descartarse aunque haya nacido desde onboarding.

### Campanas y BBDD

- No borrar campanas existentes sin auditoria.
- Clasificar campanas antes de reutilizar.
- Marcar calidad estimada.
- Marcar observaciones.
- Detectar alertas de campanas sin cliente, segmento o pais.
- Detectar duplicados.
- Marcar mala nomenclatura.

### SDR

- SDR puede asignarse por cliente y por segmento.
- La medicion SDR debe considerar actividad, reuniones, validez y resultado comercial.
- Rankings SDR son idea futura, no formula aprobada.

### Reuniones

- Reuniones tienen validacion Conprospeccion.
- Reuniones tienen validacion cliente.
- La validez final depende de ambas validaciones.
- Las disputas deben quedar marcadas.
- El estado comercial debe separarse de la validez de la reunion.

### Revenue Intelligence

- Debe mostrar lectura ejecutiva y accionable.
- Debe conectar embudo, segmentos, campanas y decisiones.
- Debe orientar decisiones futuras, no solo reportar actividad pasada.

## Backlog Estrategico

Ideas futuras registradas sin compromiso de implementacion inmediata:

- Rankings SDR globales.
- Rankings SDR por cliente.
- Rankings SDR por segmento.
- Rankings SDR por canal.
- Medicion por horario.
- Medicion por dia de la semana.
- Medicion por pais.
- Medicion por industria.
- Medicion por cargo.
- Medicion por tamano de empresa.
- Prediccion de cumplimiento contractual.
- Prediccion de reuniones validas.
- Prediccion de capacidad SDR.
- Recomendaciones automaticas de segmentos.
- Recomendaciones automaticas de campanas.
- Recomendaciones automaticas de reasignacion SDR.
- Aprendizaje historico por cliente.
- Aprendizaje historico por industria.
- Inteligencia comercial por vertical.
- Benchmark entre clientes similares.
- Benchmark entre segmentos similares.
- Benchmark entre campanas similares.
- Score de cuenta.
- Score de prospecto.
- Score de campana.
- Score de base de datos.
- Score de readiness de setup.
- Deteccion de duplicados cross-platform.
- Auditoria de nomenclatura.
- Auditoria de dominios y correos.
- Alertas de reputacion de email.
- Alertas de warmup.
- Alertas de SLA de validacion.
- Alertas de setup bloqueado.
- Motor de recomendaciones con IA.
- Libreria historica de ICP ganadores.
- Libreria historica de mensajes ganadores.
- Reportes ejecutivos automaticos.
- Simulador de capacidad.
- Simulador de escenarios de campana.
- Deteccion de saturacion de mercado.
- Deteccion de oportunidades de upsell.
- Revenue forecast.
- Pipeline forecast.
- Analisis de conversion por etapa.
- Analisis de calidad por fuente: Apollo, Snov, CSV, GHL.

## Decisiones Abiertas

- Repositorio canonico para documentacion permanente: repo historico `ConprospeccionOS` vs repo desplegado `conprospeccionOS2026`.
- Modelo final de autenticacion y roles.
- Separacion exacta entre portal cliente e interno.
- Politica de permisos para cliente, SDR, operaciones, liderazgo y admin.
- Modelo final de Supabase.
- Politica de RLS.
- Orden de integraciones reales: Apollo, Snov, GHL, Hostinger, Zapmail.
- Criterio de calidad para BBDD.
- Criterio de calidad para campanas.
- Criterio de descarte de segmentos.
- Criterio para pausar segmentos.
- Formula de ranking SDR.
- Formula de readiness del setup.
- Formula de score de campana.
- Formula de score de ICP.
- Como versionar cambios de ICP.
- Como versionar cambios de validacion.
- Como mapear historicos GBS.
- Como resolver duplicados entre carpetas, Supabase y plataformas externas.
- Que datos del cliente son visibles para cliente vs internos.
- Como manejar datos sensibles.
- Como medir revenue real.
- Como conectar resultados comerciales con facturacion.
- Como representar multiples clientes activos.
- Como manejar clientes con multiples paises y unidades de negocio.
- Convenciones de nombres para dominios.
- Convenciones de nombres para correos.
- Convenciones de nombres para campanas.
- Convenciones de nombres para BBDD.
- Proveedor final de correos.
- Proveedor final de dominios.
- Politica de warmup.
- Politica de rotacion de casillas.
- Politica de archival de campanas antiguas.

## Vision A 3 Anos

En tres anos, Conprospeccion OS deberia ser el sistema operativo comercial que permita a Conprospeccion escalar prospeccion B2B con inteligencia acumulativa.

La vision no es solo administrar campanas. La vision es crear una memoria comercial viva que aprenda:

- Que clientes son mas faciles de activar.
- Que industrias convierten mejor.
- Que paises responden mejor.
- Que cargos generan mejores reuniones.
- Que tamanos de empresa tienen mejor fit.
- Que mensajes funcionan por vertical.
- Que SDR rinden mejor en cada contexto.
- Que campanas merecen escalarse.
- Que bases deben descartarse temprano.
- Que configuraciones operativas generan riesgo.

Client Setup OS deberia ser el punto de partida operativo de cada cliente. Desde ahi, el sistema deberia crear una ruta controlada hacia datos, campanas, SDR, reuniones, validacion y revenue.

Revenue Intelligence deberia convertirse en la capa ejecutiva que responde preguntas como:

- Donde estamos ganando.
- Donde estamos perdiendo.
- Que debemos pausar.
- Que debemos escalar.
- Que cliente requiere mas capacidad.
- Que segmento tiene mas potencial.
- Que aprendizaje se puede reutilizar en otro cliente.

El sistema deberia evolucionar desde dashboards descriptivos hacia inteligencia prescriptiva:

1. Primero mostrar datos.
2. Luego explicar causas.
3. Luego recomendar acciones.
4. Luego predecir resultados.
5. Finalmente automatizar partes del flujo con control humano.

La meta estrategica es que cada cliente nuevo parta con menos incertidumbre que el anterior, porque Conprospeccion OS habra acumulado aprendizaje historico de clientes, segmentos, campanas, SDR y resultados.

## No Objetivos De Esta Fase

- No implementar nuevas pantallas.
- No conectar APIs reales.
- No conectar Supabase.
- No migrar datos.
- No borrar archivos.
- No refactorizar codigo.
- No cerrar decisiones abiertas.
- No convertir todas las ideas en funcionalidades.

## Criterio Para Futuras Actualizaciones

Cada nueva decision debe agregarse a este documento con estado explicito:

- Decision aprobada
- Hipotesis
- Idea futura
- Pendiente de definicion

Si una hipotesis se valida, debe moverse a Decision aprobada.

Si una idea se descarta, debe conservarse con nota de descarte y fecha, no borrarse sin contexto.
