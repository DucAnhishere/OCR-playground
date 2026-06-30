# Use official Node.js Alpine image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package configuration files for caching dependencies
COPY package.json package-lock.json* ./

# Install npm dependencies from the lockfile for reproducible builds
RUN npm ci

# Copy the rest of the application files
COPY . .

# Expose Vite's default dev port
EXPOSE 5173

# Start Vite dev server and bind to 0.0.0.0 so it is accessible outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
