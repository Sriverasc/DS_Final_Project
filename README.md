# 🚀 Sistema P2P de Transferencia de Archivos con Tracker

Este proyecto implementa un sistema **Peer-to-Peer (P2P)** en Python que permite la transferencia eficiente de archivos entre nodos, utilizando un **tracker centralizado** para la localización de peers.

---

## 📌 Descripción

El sistema está compuesto por:

- 🧭 **Tracker**: Coordina la red y mantiene un registro de qué nodo posee cada archivo.
- 🔗 **Peers (nodos)**: Actúan como clientes y servidores simultáneamente para compartir archivos.

Los peers pueden:
- Anunciar archivos disponibles
- Consultar archivos en la red
- Descargar archivos desde otros nodos
- Reanudar descargas incompletas

---

## 🧠 Características principales

✅ Transferencia de archivos por **chunks (fragmentos)**  
✅ Soporte para **reanudación de descargas**  
✅ Comunicación mediante **sockets TCP**  
✅ Sistema tolerante a fallos con **reintentos automáticos**  
✅ Manejo concurrente con **multithreading**  
✅ Persistencia de estado en archivos JSON  
✅ Barra de progreso con `tqdm`  

---

## 🏗️ Arquitectura del sistema
```
       +------------------+
       |     Tracker      |
       |  (Centralizado)  |
       +--------+---------+
                |
    -----------------------------
    |            |             |
 Peer A       Peer B        Peer C
```

---

## 📂 Estructura del proyecto
```
.
├── tracker.py # Servidor central (tracker)
├── peer.py # Implementación de nodos
├── archivos_nodo_a/ # Archivos del peer A
├── archivos_nodo_b/ # Archivos del peer B
├── archivos_nodo_c/ # Archivos del peer C
└── peer_X_state.json # Estado persistente de cada peer
```
---

## ⚙️ Requisitos

- Python 3.8+
- Librerías:

```
pip install tqdm
```

🚀 Cómo ejecutar el proyecto
1️⃣ Iniciar el tracker
python tracker.py

Esto iniciará el servidor central que coordina la red.

2️⃣ Ejecutar un peer
python peer.py

Se te pedirá ingresar el ID del nodo:

Ingresa el ID del nodo (A, B o C):

Cada peer:

Usa un puerto distinto
Tiene su propio directorio de archivos

📡 Protocolo de comunicación

🔹 Mensajes soportados
Peer → Tracker
ANNOUNCE <file> <peer_id> <port>
LIST_FILES
Peer → Peer
SIZE <file> → obtiene tamaño
GET <file> <start> <end> → descarga chunk

📥 Flujo de descarga
El peer solicita peers disponibles al tracker
Se conecta a uno de ellos
Obtiene el tamaño del archivo
Descarga por partes (chunks de 1MB)
Guarda progreso y permite reanudar

🔁 Tolerancia a fallos
Reintentos automáticos en:
Conexión al tracker
Descargas fallidas
Eliminación de archivos corruptos
Manejo de timeouts
💾 Persistencia

Cada peer guarda su estado en:

peer_<ID>_state.json

Esto permite:

Recordar archivos disponibles
Continuar descargas previas
🖥️ Interfaz de usuario

Cada peer tiene un menú interactivo:

1. Mostrar lista de Archivos
2. Descargar Archivo
3. Salir

📊 Ejemplo de uso
- Inicia el tracker
- Ejecuta múltiples peers
- Coloca archivos en un nodo
- Descarga desde otro nodo
🧪 Posibles mejoras
 - 🔐 Encriptación de conexiones
 - 📦 Distribución paralela (multi-peer download)
 - 🌐 Interfaz web
 - 📊 Métricas de rendimiento
 - 🔎 Búsqueda avanzada de archivos

👨‍💻 Autores

 - Sebastián Rivera Santa Cruz
 - Hernández Arzate Job Gerardo
 - Archundia Jiménez Marco Tulio

📄 Licencia

Este proyecto es de uso académico y educativo.
