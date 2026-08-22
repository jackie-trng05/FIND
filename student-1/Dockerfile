# Dockerfile for Student 1 backend placeholder service
# Builds the backend code found in ./backend and runs it on port 5001

FROM node:18-alpine
WORKDIR /usr/src/app

# Install only production dependencies for the placeholder service
COPY backend/package*.json ./
RUN npm install --production

# Copy backend sources
COPY backend/ ./

EXPOSE 5001

CMD ["node", "index.js"]
