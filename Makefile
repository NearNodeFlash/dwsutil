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

.PHONY: init test
