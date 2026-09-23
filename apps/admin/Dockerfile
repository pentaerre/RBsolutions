FROM node:22-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV WATCHPACK_POLLING=true
EXPOSE 3001

CMD ["npm", "run", "dev"]
