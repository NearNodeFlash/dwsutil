USER=$(shell id -un)

PROD_VERSION=$(shell grep "DWSUTIL_VERSION =" pkg/Config.py | sed 's/[^0-9.]//g')
DEV_REPONAME=dwsutil
DEV_IMGNAME=dwsutil
DTR_IMGPATH=arti.dev.cray.com/$(DEV_REPONAME)/$(DEV_IMGNAME)
LOCAL_IMGPATH=$(DEV_IMGNAME)
DOCKER_IMAGES=$(shell docker images | grep dwsutil | awk '{printf "%s:%s ",$$1,$$2}')
init:
	pip3 install -r requirements.txt

test:
	python3 -m unittest discover -s tests/ -v 2>&1 | tee tests/results.txt

# Run coverage but display nothing
coverage:
	coverage run --branch --timid --source=. --omit=tests/* -m unittest discover -s tests/ -v 2>&1 | tee tests/results.txt

# Run coverage and display text output
coveragereport: coverage
	coverage report --skip-empty

# Show coverage will run a coverage report and display in HTML on MacOS
coveragehtml: coverage
	coverage html --skip-empty 

# Show coverage will run a coverage report and display in HTML on MacOS
showcoverage: coveragehtml
	open htmlcov/index.html

image:
	docker build --rm --file Dockerfile --label $(DTR_IMGPATH):$(PROD_VERSION) --tag $(LOCAL_IMGPATH):$(PROD_VERSION) .
	docker tag  $(LOCAL_IMGPATH):$(PROD_VERSION) $(DTR_IMGPATH):$(PROD_VERSION) 

docker-clean:
	@echo Deleting $(DOCKER_IMAGES)
	docker rmi -f $(shell docker images | grep dwsutil | awk '{printf "%s:%s ",$$1,$$2}')

# push:
# 	docker push $(DTR_IMGPATH):$(PROD_VERSION)

container-unit-test:
	docker build -f Dockerfile --label $(DTR_IMGPATH)-$@:$(PROD_VERSION)-$@ -t $(DTR_IMGPATH)-$@:$(PROD_VERSION) --target $@ .
	docker run --rm -t --name $@  $(DTR_IMGPATH)-$@:$(PROD_VERSION)

.PHONY: init test
