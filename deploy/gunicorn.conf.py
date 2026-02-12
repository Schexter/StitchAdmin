# Gunicorn Konfiguration für StitchAdmin 2.0
import multiprocessing

# Server Socket
bind = "127.0.0.1:8000"

# Worker-Prozesse
workers = 3
worker_class = "sync"
timeout = 120

# Logging
accesslog = "/opt/stitchadmin/logs/access.log"
errorlog = "/opt/stitchadmin/logs/error.log"
loglevel = "info"

# Prozess
pidfile = "/opt/stitchadmin/gunicorn.pid"
daemon = False
