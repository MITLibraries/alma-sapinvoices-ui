ECR_NAME_DEV:=alma-sapinvoices-ui-dev
ECR_URL_DEV:=222053980223.dkr.ecr.us-east-1.amazonaws.com/alma-sapinvoices-ui-dev

SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)

help: # Preview Makefile commands
	@awk 'BEGIN { FS = ":.*#"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*#/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

#######################
# Dependency commands
#######################

install: # Install Python dependencies
	pipenv install --dev
	pipenv run pre-commit install

update: install # Update Python dependencies
	pipenv clean
	pipenv update --dev

fetch-mitlib-style: # Fetch MIT Libraries style guide
	mkdir -p tmp
	curl -o tmp/assets.zip https://codeload.github.com/MITLibraries/mitlib-style/zip/master
	unzip -o -d tmp tmp/assets.zip 
	# Copy the compiled stylesheet
	cp tmp/mitlib-style-master/dest/css/libraries-main.min.css webapp/static/libraries-main.min.css

######################
# Unit test commands
######################

test: # Run tests and print a coverage report
	pipenv run coverage run --source=lambdas,webapp -m pytest -vv
	pipenv run coverage report -m

coveralls: test # Write coverage data to an LCOV report
	pipenv run coverage lcov -o ./coverage/lcov.info

####################################
# Code quality and safety commands
####################################

lint: black mypy ruff safety # Run linters

black: # Run 'black' linter and print a preview of suggested changes
	pipenv run black --check --diff .

mypy: # Run 'mypy' linter
	pipenv run mypy .

ruff: # Run 'ruff' linter and print a preview of errors
	pipenv run ruff check .

safety: # Check for security vulnerabilities and verify Pipfile.lock is up-to-date
	pipenv check --ignore 70612
	pipenv verify

lint-apply: # Apply changes with 'black' and resolve 'fixable errors' with 'ruff'
	black-apply ruff-apply 

black-apply: # Apply changes with 'black'
	pipenv run black .

ruff-apply: # Resolve 'fixable errors' with 'ruff'
	pipenv run ruff check --fix .

######################################################################
# Terraform-generated Developer Deploy Commands for Dev environment
######################################################################
dist-dev: # Build Docker image for Dev
	docker build --platform linux/amd64 \
		-t $(ECR_URL_DEV):latest \
		-t $(ECR_URL_DEV):`git describe --always` \
		-t $(ECR_NAME_DEV):latest .

publish-dev: dist-dev # Build, tag, and push Docker image for Dev
	docker login -u AWS -p $$(aws ecr get-login-password --region us-east-1) $(ECR_URL_DEV)
	docker push $(ECR_URL_DEV):latest
	docker push $(ECR_URL_DEV):`git describe --always`
	
######################################################################
# Terraform-generated Developer Deploy Commands for Stage environment
# This requires that ECR_NAME_STAGE, ECR_URL_STAGE, and FUNCTION_STAGE
# environment variables are set locally by the developer and that the
# developer has authenticated to the correct AWS Account. The values
# for the environment variables can be found in the stage_build.yml 
# caller workflow.   
######################################################################
