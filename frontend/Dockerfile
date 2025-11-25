## Frontend Dockerfile (production)
## IMPORTANT: We build the React app LOCALLY and upload `frontend/build/` to EC2.
## This image ONLY serves the already-built static files with Nginx.

FROM nginx:alpine

WORKDIR /usr/share/nginx/html

# Copy pre-built React app from local `build/` directory
COPY ./build ./

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
