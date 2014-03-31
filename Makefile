
CHART_FONTS = unhinted/Noto*-Regular.ttf

chart.pdf: chart.py $(CHART_FONTS)
	@echo "Generating $@"
	@python $^
