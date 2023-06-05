ifndef RADIUS
RADIUS=0.6
endif

ifndef BATCH
BATCH=32
endif

ifndef DART
DART=python manage.py
endif

.phony: eval typecheck eval-all video test

eval:
	$(DART) evaluate -p $(TARGET) -b $(BATCH)
	$(DART) examples -p $(TARGET)

video:
	$(DART) evaluate -p $(TARGET) -a -b 1
	$(DART) evaluate -p $(TARGET) -ac -b 1
	$(DART) video -p $(TARGET)

mri:
	$(DART) map -p $(TARGET) -l -3.0 -3.0 -1.0 -u 3.0 3.0 3.0 -r 512 -b 16
	$(DART) slice -p $(TARGET)

typecheck:
	python -m mypy train.py
	python -m mypy manage.py

test:
	python train.py ngp -s data/cabinets/cabinets.json -o results/test -p \
		data/cabinets-000/cabinets-000.mat --norm 1e4 --min_speed 0.25 -e 1 \
		--repeat 1 --iid
