FROM node:20-alpine

WORKDIR /app

# Install deps first for better caching
COPY package.json ./
RUN npm install

# Copy app (for initial build); in dev compose we also bind-mount
COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]