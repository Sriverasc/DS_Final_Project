import socket
import threading
import os
import time

# Configuración del rastreador
HOST = '25.54.6.194'
PORT = 5000
BUFFER_SIZE = 16777216
peers = {}
lock = threading.Lock()
running = True

# Función para manejar las solicitudes de los peers
def handle_peer(conn, addr):
    try:
        data = conn.recv(BUFFER_SIZE).decode()
        request = data.split()

        if request[0] == 'ANNOUNCE':
            if len(request) != 4:
                raise ValueError("Formato de mensaje ANNOUNCE incorrecto")
            
            file_name = request[1]
            peer_id = request[2]
            peer_port = int(request[3])

            with lock:
                if file_name not in peers:
                    peers[file_name] = {}
                peers[file_name][peer_id] = (addr[0], peer_port)

                peer_list = [f"{p_id}|{ip}:{port}" for p_id, (ip, port) in peers[file_name].items() if p_id != peer_id]
                response = ",".join(peer_list).encode() if peer_list else b"NO_PEERS"
                conn.sendall(response)

        elif request[0] == 'LIST_FILES':
            with lock:
                file_list = "\n".join([f"{file} (Nodo {peer_id})" for file, peers_list in peers.items() for peer_id in peers_list])
            conn.sendall(file_list.encode() if file_list else b"NO_FILES")

    except ValueError as ve:
        print(f"Error de valor al procesar la solicitud del peer {addr}: {ve}")
        conn.sendall(b"ERROR")
    except Exception as e:
        print(f"Error al procesar la solicitud del peer {addr}: {e}")
        conn.sendall(b"ERROR")
    finally:
        time.sleep(0.1)
        conn.sendall(b"OK")
        conn.close()

# Función para mostrar el estado de la red
def show_network_status():
    global running
    while running:
        with lock:
            print("\nEstado de la red:")
            for file_name, peer_list in peers.items():
                print(f"  Archivo: {file_name}")
                for peer_id, (ip, port) in peer_list.items():
                    print(f"    Peer {peer_id}: {ip}:{port}")
        print("\nSi desea salir, presione 'q'")
        time.sleep(5)
        if input().lower() == 'q':
            with lock:
                running = False
                break

# Main loop
if __name__ == '__main__':
    status_thread = threading.Thread(target=show_network_status, daemon=True)
    status_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Rastreador escuchando en {HOST}:{PORT}")
        s.settimeout(1)
        while running:
            try:
                conn, addr = s.accept()
                threading.Thread(target=handle_peer, args=(conn, addr)).start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error en el bucle principal del tracker: {e}")
                break

    status_thread.join()
    print("Tracker detenido.")
