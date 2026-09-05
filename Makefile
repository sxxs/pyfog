# Helpers for development; the FOG server only needs install.sh.
VERSION := $(shell python3 -c "import pyfog; print(pyfog.__version__)")

.PHONY: test smoke dist clean

test:            ## unit tests, no database
	python3 -m unittest

smoke:           ## every command against the seeded MariaDB in Docker
	docker compose run --rm --entrypoint tests/smoke.sh pyfog
	docker compose down -v

dist:            ## dist/pyfog-VERSION.tar.gz from the last commit, for scp to the server
	mkdir -p dist
	git archive --format=tar.gz --prefix=pyfog-$(VERSION)/ -o dist/pyfog-$(VERSION).tar.gz HEAD
	@ls -l dist/pyfog-$(VERSION).tar.gz

clean:
	rm -rf dist build *.egg-info
	find . -name __pycache__ -prune -exec rm -rf {} +
