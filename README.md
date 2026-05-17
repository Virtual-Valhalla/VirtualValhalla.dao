### 2. `README.md` - Local Development Guide

```markdown
# ⚡ NEWS_GLOBO | Terminal de Monitoreo Geoespacial

Stack: Python 3.12 (Flask) + SQLite (WAL Mode) + Globe.gl (Three.js).

### Configuración de Ingeniería
1. **Entorno:** 
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o .\venv\Scripts\activate en Windows
   ```
2. **Dependencias:** `pip install -r requirements.txt`.
3. **Persistencia:** La base de datos se inicializa automáticamente en modo **WAL** para permitir concurrencia entre el Scheduler y la API.
4. **Ejecución:** `python app.py`.

### Arquitectura de Datos
El sistema utiliza una **hibridación de tres capas**:
* **L1 (Caché):** Memoria local con TTL (6h para países, 4h para feed global).
* **L2 (DB Local):** Artículos scrapeados por el scheduler en background cada 60 min.
* **L3 (API Externa):** NewsAPI con rotación automática de keys si se alcanza el rate limit.
```

---

