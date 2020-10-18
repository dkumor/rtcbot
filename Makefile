.PHONY: clean test phony 

# Empty rule for forcing rebuilds
phony:

js/node_modules:
	cd js; npm i

js: phony js/node_modules
	cd js; npm run build
	cp js/dist/rtcbot.umd.js rtcbot/rtcbot.js

dist: js phony
	rm -rf ./dist
	python setup.py sdist bdist_wheel

publish: dist phony
	cd js; npm publish
	twine upload dist/*
	anaconda upload dist/*.tar.gz

test: phony
	pytest --cov=rtcbot --timeout=20
	# cd js; npm run test # js tests don't work right now

docs: phony
	cd docs; make html

clean: phony
	rm -rf ./dist
	rm -rf ./js/dist
	rm -f ./rtcbot/rtcbot.js
	rm -rf ./docs/_build