.PHONY: build run test clean docker-build docker-run proto

# Build the application
build:
	go build -o vessel-llm-router ./cmd/server

# Run the application
run:
	go run ./cmd/server/main.go

# Run tests
test:
	go test -v ./...

# Clean build artifacts
clean:
	rm -f vessel-llm-router
	go clean

# Generate protobuf code
proto:
	protoc --go_out=. --go-grpc_out=. proto/llm.proto

# Build Docker image
docker-build:
	docker build -t vessel-llm-router:latest .

# Run Docker container
docker-run:
	docker run -p 8082:8082 -p 8083:8083 \
		-e OPENAI_API_KEY=${OPENAI_API_KEY} \
		-e REDIS_URL=${REDIS_URL} \
		vessel-llm-router:latest

# Download dependencies
deps:
	go mod download
	go mod tidy

# Format code
fmt:
	go fmt ./...

# Run linter
lint:
	golangci-lint run

# Show help
help:
	@echo "Available targets:"
	@echo "  build        - Build the application"
	@echo "  run          - Run the application"
	@echo "  test         - Run tests"
	@echo "  clean        - Clean build artifacts"
	@echo "  proto        - Generate protobuf code"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  deps         - Download and tidy dependencies"
	@echo "  fmt          - Format code"
	@echo "  lint         - Run linter"
	@echo "  help         - Show this help message"