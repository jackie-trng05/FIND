FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

ENV NODE_ENV=development
ENV PORT=5001

EXPOSE 5001

CMD ["node", "index.js"]