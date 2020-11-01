@default_files = ('index.tex');
$out_dir = 'target';

$pdf_mode = 1;
$pdflatex = 'TEXINPUTS=".:./sty:$TEXINPUTS" lualatex -interaction=nonstopmode -shell-escape';

add_cus_dep('Rnw', 'tex', 1, 'knitrlatex');
sub knitrlatex {
  system("Rscript -e \"knitr::knit('$_[0].Rnw')\"");
}
