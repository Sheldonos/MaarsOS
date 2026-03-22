# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache git

# Copy all source code
COPY . .

# Download dependencies and generate go.sum
RUN go mod download && go mod tidy

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o vessel-gateway .

# Runtime stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates curl

WORKDIR /root/

# Copy binary from builder
COPY --from=builder /app/vessel-gateway .

# Expose port
EXPOSE 8000

# Run the binary
CMD ["./vessel-gateway"]