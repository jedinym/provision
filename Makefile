IMAGE_NAME = provision
ENGINE = docker

ENDPOINT_SRC = ./src/endpoint/

.PHONY: proto
proto:
	protoc -I . --python_betterproto_out=src/ src/endpoint/endpoint.proto

.PHONY: provision
$(IMAGE_NAME): $(IMAGE_NAME)/Containerfile
	$(ENGINE) build . -t $@ -f $^

.PHONY: run
run: $(IMAGE_NAME)
	$(ENGINE) -it $(IMAGE_NAME) /bin/bash

