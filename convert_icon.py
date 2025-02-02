from cairosvg import svg2png

with open('static/icons/icon-192x192.svg', 'rb') as svg_file:
    svg2png(file_obj=svg_file,
            write_to='static/icons/icon-192x192.png',
            output_width=192,
            output_height=192) 