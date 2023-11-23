
IMAGE_NAME = provision

.PHONY: all
all: $(IMAGE_NAME)

.PHONY: provision
$(IMAGE_NAME): $(IMAGE_NAME)/Dockerfile
	docker build . -t $@ -f $^

.PHONY: run
run: $(IMAGE_NAME)
	docker run -it $(IMAGE_NAME) /bin/bash

