FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

ENV NODE_ENV=development
ENV PORT=6001

EXPOSE 6001

CMD ["node", "index.js"]