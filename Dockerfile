FROM node:22-alpine
WORKDIR /workspace
COPY app/package*.json ./app/
WORKDIR /workspace/app
RUN npm install
EXPOSE 5173
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
