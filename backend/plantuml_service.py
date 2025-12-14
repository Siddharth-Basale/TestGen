"""
PlantUML service for generating and rendering diagrams
"""
import subprocess
from pathlib import Path
import tempfile
import os

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).resolve().parent

# Look for plantuml.jar in the same directory as this script
PLANTUML_JAR = SCRIPT_DIR / "plantuml.jar"


def render_plantuml_from_text(puml_text: str, output_dir: str = None, filename_base: str = "plantuml"):
    """
    Write a .puml and call local plantuml.jar to render a PNG.
    
    Args:
        puml_text: PlantUML code as string
        output_dir: Directory to save output (if None, uses temp directory)
        filename_base: Base name for output files
    
    Returns:
        tuple: (png_file_path, puml_file_path) - paths to generated files
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    puml_file = outdir / f"{filename_base}.puml"
    png_file = outdir / f"{filename_base}.png"
    
    # Write PlantUML code to file
    puml_file.write_text(puml_text, encoding="utf-8")
    
    if not PLANTUML_JAR.exists():
        raise FileNotFoundError(f"plantuml.jar not found at {PLANTUML_JAR}")
    
    # Call PlantUML to generate PNG
    cmd = ["java", "-jar", str(PLANTUML_JAR), "-tpng", str(puml_file), "-charset", "UTF-8"]
    subprocess.run(cmd, check=True, cwd=str(outdir))
    
    # PlantUML usually writes png alongside the puml file
    if not png_file.exists():
        # PlantUML may name output differently; search for *.png in outdir matching filename_base
        matches = list(outdir.glob(f"{filename_base}*.png"))
        if matches:
            return (str(matches[0]), str(puml_file))
        raise FileNotFoundError("PlantUML did not produce a PNG.")
    
    return (str(png_file), str(puml_file))

