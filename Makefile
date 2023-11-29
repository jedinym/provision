IMAGE_NAME = provision
ENGINE = docker

.PHONY: all
all: $(IMAGE_NAME)

.PHONY: provision
$(IMAGE_NAME): $(IMAGE_NAME)/Containerfile
	$(ENGINE) build . -t $@ -f $^

.PHONY: run
run: $(IMAGE_NAME)
	$(ENGINE) -it $(IMAGE_NAME) /bin/bash

