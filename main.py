import eel
import sys

# Initialize Eel with the folder containing your web assets
eel.init('web')

@eel.expose
def greet_from_python(name):
    """
    This function is exposed to the JavaScript side.
    It takes a name and returns a greeting string.
    """
    print(f"Greeting requested for: {name}")
    return f"Hello, {name}! Message from Python."

def start_app():
    try:
        # Start the application
        # mode='chrome' (default) tries to open Chrome. 
        # mode='edge' or mode='default' uses the system default browser.
        # size=(width, height) sets the initial window size
        print("Starting Eel app...")
        eel.start('main.html', size=(800, 600))
    except (SystemExit, KeyboardInterrupt):
        print("Closing app...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        # Fallback: if browser fails to launch, you might see an error here.
        # Often happens if Chrome/Edge isn't installed or found.
        # You can try mode='default' to use the system default browser if chrome fails.
        if "can't find" in str(e).lower():
             print("Chrome not found, retrying with default browser...")
             eel.start('main.html', mode='default', size=(800, 600))

if __name__ == '__main__':
    start_app()
