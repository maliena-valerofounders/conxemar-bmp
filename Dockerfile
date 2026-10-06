# Web estática de Conxemar servida con nginx. Cloud Run inyecta PORT (8080 por defecto).
FROM nginx:1.27-alpine
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY index.html manifest.webmanifest sw.js /usr/share/nginx/html/
ENV PORT=8080
EXPOSE 8080
