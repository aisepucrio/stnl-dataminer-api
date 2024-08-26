import subprocess
import os

def run_rust_feature_mining():
    # Caminho para o executável ou script Rust
    rust_executable = os.path.join(os.path.dirname(__file__), 'path_to_your_rust_executable')

    try:
        # Executa o código Rust como subprocesso
        result = subprocess.run([rust_executable], capture_output=True, text=True)

        # Verifica se a execução foi bem-sucedida
        if result.returncode == 0:
            print("Rust code executed successfully.")
            print("Output:", result.stdout)
        else:
            print("Rust code failed with error.")
            print("Error Output:", result.stderr)
    
    except Exception as e:
        print(f"An error occurred: {e}")
