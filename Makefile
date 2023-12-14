.PHONY: endpoint
endpoint: check-env
	docker buildx build --ssh default=$$SSH_AUTH_SOCK -f Dockerfile.endpoint -t sqc-endpoint .

.PHONY:check-env
check-env:
ifndef SSH_AUTH_SOCK
	$(error SSH_AUTH_SOCK is undefined (is the ssh-agent not running?))
endif
