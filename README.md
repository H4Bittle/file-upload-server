# file-upload-server

Small Flask app: a web page to drag-and-drop (or click-to-browse) files onto
your server, from any device on any network. No file-type restrictions.

## Quick start

```bash
pip install -r requirements.txt
python3 app.py
```

Then open `http://<server-ip>:8080` from any browser — on the server itself,
or from anywhere else once the port is reachable (see "Expose it" below).

Uploaded files are written to `./uploads/` next to `app.py`.

## Config (environment variables)

| Variable        | Default          | Purpose                                              |
|-----------------|------------------|-------------------------------------------------------|
| `HOST`          | `0.0.0.0`        | Interface to bind. `0.0.0.0` = all interfaces.        |
| `PORT`          | `8080`           | Port to listen on.                                    |
| `UPLOAD_DIR`    | `./uploads`      | Where uploaded files are stored.                       |
| `MAX_UPLOAD_MB` | `10240` (10 GB)  | Per-file size cap. Set to `0` for no limit.            |
| `UPLOAD_USER`   | *(unset)*        | If set together with `UPLOAD_PASS`, HTTP Basic Auth is required for every route. |
| `UPLOAD_PASS`   | *(unset)*        | See above.                                             |

Example with auth enabled and a custom port:

```bash
UPLOAD_USER=cheif UPLOAD_PASS='pick-something-strong' PORT=9000 python3 app.py
```

Since you're exposing this to the open internet, I'd turn auth on — it's one
env var pair, and the alternative is anyone who finds the URL can fill your
disk or drop files on your box.

## Keep it running after you close the SSH session

**Option A — nohup (quick and dirty):**
```bash
nohup python3 app.py > server.log 2>&1 &
disown
```

**Option B — tmux (lets you reattach and watch logs):**
```bash
tmux new -s upload
python3 app.py
# Ctrl+B then D to detach; `tmux attach -t upload` to come back
```

**Option C — systemd (survives reboots, restarts on crash):**

Create `/etc/systemd/system/upload-server.service`:
```ini
[Unit]
Description=file-upload-server
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/file-upload-server
Environment=UPLOAD_USER=cheif
Environment=UPLOAD_PASS=pick-something-strong
ExecStart=/usr/bin/python3 /path/to/file-upload-server/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now upload-server
```

## Expose it to the internet

If this is a cloud VM with a public IP, two things need to allow the port
(default `8080`):

```bash
# OS firewall, if ufw is active
sudo ufw allow 8080/tcp
```
Plus whatever sits in front of the VM — a cloud security group / firewall
rule (AWS/GCP/Azure/DigitalOcean all have one) needs an inbound allow rule
for that port too.

If it's *not* on a public IP (behind home/office NAT), skip firewall/router
config entirely and use a tunnel instead — no port forwarding needed, and
you get HTTPS for free:

```bash
# ngrok
ngrok http 8080

# or Cloudflare Tunnel
cloudflared tunnel --url http://localhost:8080
```

Either prints a public `https://...` URL that forwards straight to the app.
This is also the easier path even on a public-IP box, since it avoids
sending Basic Auth credentials over plain HTTP.

## Notes

- Filenames are sanitized (`werkzeug.secure_filename`) to block path
  traversal; a same-named file gets `_1`, `_2`, etc. appended rather than
  overwriting.
- No file type is blocked — anything can be uploaded, as-is.
- The built-in Flask server is fine for personal use; for heavy concurrent
  traffic, put it behind `gunicorn` + `nginx` instead.
