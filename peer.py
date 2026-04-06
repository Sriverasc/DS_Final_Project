import socket
import threading
import os
import json
import time
from tqdm import tqdm

class Peer:
    def __init__(self, peer_id, tracker_host, tracker_port, files_dir, peer_port):
        self.peer_id = peer_id
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.files_dir = files_dir
        self.peer_port = peer_port
        self.BUFFER_SIZE = 16777216  # 16 MB para una transferencia más eficiente

        self.files = self.get_files_from_directory()
        self.load_state()  # Cargar el estado al iniciar

        self.announce_files()
        self.start_server()

    def get_files_from_directory(self):
        return [f for f in os.listdir(self.files_dir) if os.path.isfile(os.path.join(self.files_dir, f))]

    def load_state(self):
        state_file = f"peer_{self.peer_id}_state.json"
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                self.files = state.get('files', [])

    def save_state(self):
        state = {
            'files': self.files,
        }
        state_file = f"peer_{self.peer_id}_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f)

    def announce_files(self):
        for file in self.files:
            file_path = os.path.join(self.files_dir, file)
            if os.path.exists(file_path):
                self.send_to_tracker(f"ANNOUNCE {file} {self.peer_id} {self.peer_port}")
            else:
                print(f"Advertencia: El archivo {file} no existe en {file_path}")

    def send_to_tracker(self, message):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with socket.socket() as s:
                    s.settimeout(5)  # Timeout de 5 segundos
                    s.connect((self.tracker_host, self.tracker_port))
                    s.sendall(message.encode())
                    response = s.recv(self.BUFFER_SIZE).decode()
                    return response
            except (socket.timeout, ConnectionResetError) as e:
                print(f"Error al comunicarse con el tracker (intento {attempt + 1}): {e}")
                time.sleep(1)  # Esperar antes de reintentar
        print("No se pudo conectar al tracker después de varios intentos")
        return None

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.peer_port))
        self.server_socket.listen()
        print(f"Nodo {self.peer_id} ")
        threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self):
        while True:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_request, args=(conn, addr)).start()
            except Exception as e:
                print(f"Error al aceptar conexión: {e}")

    def handle_request(self, conn, addr):
        try:
            while True:
                data = conn.recv(self.BUFFER_SIZE).decode()
                if not data:
                    break
                request = data.split()
                if request[0] == 'GET':
                    file_name, start_byte, end_byte = request[1], int(request[2]), int(request[3])
                    file_path = os.path.join(self.files_dir, file_name)
                    if file_name in self.files and os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            f.seek(start_byte)
                            chunk = f.read(end_byte - start_byte + 1)
                            conn.sendall(chunk)
                    else:
                        conn.sendall(b'')
                elif request[0] == 'SIZE':
                    file_name = request[1]
                    file_path = os.path.join(self.files_dir, file_name)
                    if file_name in self.files and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        conn.sendall(file_size.to_bytes(8, 'big'))
                    else:
                        conn.sendall((0).to_bytes(8, 'big'))  # Indicar archivo no encontrado
        except ConnectionAbortedError:
            print(f"Conexión abortada por el cliente {addr}")
        except Exception as e:
            print(f"Error al manejar la solicitud de {addr}: {e}")
        finally:
            conn.close()

    def download_file(self, file_name, peer_id, peer_address):
        os.makedirs(self.files_dir, exist_ok=True)
        file_path = os.path.join(self.files_dir, file_name)
        retries = 0
        max_retries = 5
        chunk_size = 1024 * 1024  # 1 MB por chunk

        while retries < max_retries:
            try:
                with socket.socket() as s:
                    s.settimeout(30)  # Timeout de 30 segundos
                    s.connect(peer_address)
                    print(f"Conectado a {peer_address} para descargar {file_name}")

                    # Obtener el tamaño total del archivo del peer
                    s.sendall(f"SIZE {file_name}".encode())
                    total_size_bytes = s.recv(8)
                    if not total_size_bytes:
                        raise Exception("No se recibió el tamaño total del archivo")
                    total_size = int.from_bytes(total_size_bytes, 'big')
                    print(f"Tamaño total del archivo: {total_size} bytes")

                    # Verificar si el archivo existe localmente
                    if os.path.exists(file_path):
                        current_size = os.path.getsize(file_path)
                        if current_size == total_size:
                            print(f"El archivo {file_name} ya está completamente descargado.")
                            return True
                        elif current_size > total_size:
                            print(f"El archivo local es más grande que el original. Eliminando y descargando de nuevo.")
                            os.remove(file_path)
                            current_size = 0
                        else:
                            print(f"Reanudando descarga desde {current_size} bytes")
                    else:
                        current_size = 0

                    # Iniciar barra de progreso
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=file_name, initial=current_size, dynamic_ncols=True) as progress:
                        with open(file_path, 'ab') as f:
                            while current_size < total_size:
                                start_byte = current_size
                                end_byte = min(current_size + chunk_size - 1, total_size - 1)
                                request = f"GET {file_name} {start_byte} {end_byte}"
                                print(f"Enviando solicitud: {request}")
                                s.sendall(request.encode())
                                
                                chunk = b''
                                bytes_received = 0
                                while bytes_received < (end_byte - start_byte + 1):
                                    part = s.recv(min(8192, end_byte - start_byte + 1 - bytes_received))
                                    if not part:
                                        raise Exception("Conexión cerrada inesperadamente")
                                    chunk += part
                                    bytes_received += len(part)
                                
                                f.write(chunk)
                                current_size += len(chunk)
                                progress.update(len(chunk))

                    if current_size == total_size:
                        print(f"\nDescarga de {file_name} desde Nodo {peer_id} completada. Total: {current_size} bytes")
                        self.files = self.get_files_from_directory()
                        self.save_state()
                        return True
                    else:
                        raise Exception(f"Descarga incompleta: {current_size}/{total_size} bytes")

            except Exception as e:
                print(f"\nError al descargar {file_name} desde Nodo {peer_id}: {e}")
                retries += 1
                time.sleep(2)  # Esperamos un poco más antes de reintentar

        print(f"Descarga de {file_name} fallida después de {max_retries} intentos")
        if os.path.exists(file_path):
            os.remove(file_path)  # Eliminar archivo incompleto
        return False

    def get_peers_from_tracker(self, file_name):
        response = self.send_to_tracker(f"ANNOUNCE {file_name} {self.peer_id} {self.peer_port}")
        if response and response != "NO_PEERS":
            return [peer_info.split('|') for peer_info in response.split(',') if '|' in peer_info]
        return []

    def show_available_files(self):
        response = self.send_to_tracker("LIST_FILES")
        if response and response != "NO_FILES":
            print("\nLista de Archivos:")
            for file_info in response.split('\n'):
                if file_info:
                    print(file_info)
        else:
            print("No hay archivos disponibles en la red.")

    def menu(self):
        while True:
            print("\nMenú:")
            print("1. Mostrar lista de Archivos")
            print("2. Descargar Archivo")
            print("3. Salir")
            choice = input("Elige una opción: ")

            if choice == '1':
                self.show_available_files()
            elif choice == '2':
                file_to_download = input("Ingresa el nombre del archivo que deseas descargar: ")
                peers = self.get_peers_from_tracker(file_to_download)
                if peers:
                    if file_to_download in self.files and os.path.exists(os.path.join(self.files_dir, file_to_download)):
                        print(f"El archivo {file_to_download} ya está descargado.")
                        continue
                    download_success = False
                    for peer_id, peer_addr_str in peers:
                        peer_ip, peer_port_str = peer_addr_str.split(':')
                        peer_addr = (peer_ip, int(peer_port_str))
                        if self.download_file(file_to_download, peer_id, peer_addr):
                            download_success = True
                            break
                    
                    if download_success:
                        print(f"Archivo {file_to_download} descargado (puede ser parcial).")
                        self.announce_files()  # Anunciar el nuevo archivo al tracker
                    else:
                        print(f"No se pudo descargar el archivo {file_to_download} de ningún peer.")
                else:
                    print(f"No se encontraron peers que compartan '{file_to_download}'")
            elif choice == '3':
                break
            else:
                print("Opción no válida. Intenta de nuevo.")

    def run(self):
        self.menu()

if __name__ == '__main__':
    peer_id = input("Ingresa el ID del nodo (A, B o C): ").upper()
    files_dir = f"archivos_nodo_{peer_id.lower()}"

    peer_ports = {'A': 5001, 'B': 5002, 'C': 5003}
    peer_port = peer_ports.get(peer_id)

    peer = Peer(peer_id, '25.54.6.194', 5000, files_dir, peer_port)
    peer.run()
