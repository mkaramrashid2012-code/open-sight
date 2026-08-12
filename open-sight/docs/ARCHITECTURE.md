# Architecture

Camera -> RTSP/OpenCV -> detection -> tracking -> event persistence -> PostgreSQL/pgvector -> search API -> Streamlit dashboard.

Heavy operations should become background workers as the system grows. GPU acceleration is optional; interfaces are deliberately replaceable. Search should return compact event metadata and generated clips/thumbnails rather than requiring continuous manual review.

Privacy controls should include retention, deletion, local-only defaults, credential isolation, and clear distinction between detection and identity claims.
