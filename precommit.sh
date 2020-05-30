set -e

black nototools tests
(cd tests && ./run_tests)

echo "Seems OK :)"