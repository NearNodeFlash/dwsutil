python3 -m unittest discover -s tests/ -v 2>&1 | tee tests/results.txt
grep FAIL tests/results.txt && echo "Unit tests failure" && rm tests/results.txt && exit 1 
echo "Unit tests successful" && rm tests/results.txt
