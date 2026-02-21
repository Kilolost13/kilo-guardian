# Build stage
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage  
FROM nginx:alpine
# Copy React app to /app subdirectory
COPY --from=build /app/build /usr/share/nginx/html/app
# Copy marketing page to /marketing subdirectory
COPY --from=build /app/public/marketing.html /usr/share/nginx/html/marketing/index.html
# Copy nginx config from build stage
COPY --from=build /app/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
