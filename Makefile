
CHART_FONTS = `cat LIST`

chart.pdf: chart.py LIST
	@echo "Generating $@"
	@python $< $(CHART_FONTS)
