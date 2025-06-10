from time import sleep
import network
import socket
import mysecrets as secrets
from servocontrollerv2 import ServoController

SSID1 = secrets.SSID1
SSID2 = secrets.SSID2
PASSWORD = secrets.PASSWORD

def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    networks = [
        (SSID1, PASSWORD),
        (SSID2, PASSWORD)
    ]

    for ssid, password in networks:
        print(f"Attempting to connect to {ssid}")
        wlan.connect(ssid, password)

        # Add a timeout for the connection attempt
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print('Waiting for connection...')
            sleep(1)

        if wlan.status() == 3:  # Check if the connection was successful
            ip = wlan.ifconfig()[0]
            print(f'Connected to {ssid} on {ip}')
            return ip, wlan
        else:
            print(f"Failed to connect to {ssid}")

    raise RuntimeError('Failed to connect to any network')

def open_socket(ip):
    address = (ip, 80)
    connection = socket.socket()
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reuse of the socket
    connection.bind(address)
    connection.listen(1)
    print("Server listening on port 80...")
    return connection
def webpage():
    """
    Returns a string containing the HTML for the main webpage.
    This webpage allows the user to control the robot's servos using
    two range sliders. The user can set the servo number and angle.

    The webpage also has a "Move" button that sends a GET request to the
    server with the servo number and angle. The "Stop" button sends a
    request to stop the servos.

    The HTML is returned as a string so that it can be used as the
    response to an HTTP request.
    """
    html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Servo Joystick Control</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    background-color: #f4f4f4;
                }
                .joystick-container {
                    width: 300px;
                    height: 300px;
                    background-color: #ddd;
                    border-radius: 50%;
                    margin: 50px auto;
                    position: relative;
                }
                .joystick-handle {
                    width: 60px;
                    height: 60px;
                    background-color: #444;
                    border-radius: 50%;
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    cursor: pointer;
                }
                #output {
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <h1>Servo Joystick Control</h1>
            <div class="joystick-container" id="joystick-container">
                <div class="joystick-handle" id="joystick-handle"></div>
            </div>
            <div id="output">
                <p>X: <span id="x-value">0</span></p>
                <p>Y: <span id="y-value">0</span></p>
                <button onclick="stopServos()">Stop</button>
            </div>
            <script>
            const joystickKnob = document.querySelector('.joystick-knob');
            const joystickContainer = document.querySelector('.joystick-container');
            const viewport = document.querySelector('.viewport');
            const crosshair = document.querySelector('.crosshair');
            const status = document.getElementById('status');

            let isDragging = false;
            let currentX = 150;
            let currentY = 150;
            const centerX = 150;
            const centerY = 150;
            const maxDistance = 120;

            // Joystick control
            function handleJoystickMove(clientX, clientY) {
                const rect = joystickContainer.getBoundingClientRect();
                let deltaX = clientX - rect.left - centerX;
                let deltaY = clientY - rect.top - centerY;

                // Limit the joystick movement to the container
                const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
                if (distance > maxDistance) {
                    deltaX = (deltaX / distance) * maxDistance;
                    deltaY = (deltaY / distance) * maxDistance;
                }

                currentX = centerX + deltaX;
                currentY = centerY + deltaY;

                joystickKnob.style.left = `${currentX - 30}px`;
                joystickKnob.style.top = `${currentY - 30}px`;

                // Convert joystick position to camera angles
                const panAngle = Math.round(90 + (deltaX / maxDistance) * 65);
                const tiltAngle = Math.round(90 + (deltaY / maxDistance) * 65);

                sendCommand({
                    action: 'move',
                    pan: panAngle,
                    tilt: tiltAngle
                });
            }

            joystickKnob.addEventListener('mousedown', startDragging, { passive: true });
            document.addEventListener('mousemove', moveJoystick, { passive: true });
            document.addEventListener('mouseup', stopDragging, { passive: true });

            // Touch events for mobile
            joystickKnob.addEventListener('touchstart', (e) => {
                startDragging(e.touches[0]);
            }, { passive: true });

            document.addEventListener('touchmove', (e) => {
                if (isDragging) {
                    moveJoystick(e.touches[0]);
                }
            }, { passive: true });

            document.addEventListener('touchend', stopDragging, { passive: true });

            function startDragging(e) {
                isDragging = true;
            }

            function moveJoystick(e) {
                if (isDragging) {
                    handleJoystickMove(e.clientX, e.clientY);
                }
            }

            function stopDragging() {
                isDragging = false;
            }

            // Point-to-shoot control
            viewport.addEventListener('click', (e) => {
                const rect = viewport.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                crosshair.style.left = `${x}px`;
                crosshair.style.top = `${y}px`;

                // Convert viewport coordinates to camera angles
                const panAngle = Math.round((x / viewport.clientWidth) * 180);
                const tiltAngle = Math.round((y / viewport.clientHeight) * 180);

                sendCommand({
                    action: 'move',
                    pan: panAngle,
                    tilt: tiltAngle
                });
            });

            // Camera control functions
            function takeShot() {
                sendCommand({ action: 'shoot' });
            }

            function centerCamera() {
                sendCommand({ action: 'center' });
            }

            function startPanorama() {
                sendCommand({
                    action: 'panorama',
                    num_shots: 5,
                    span_angle: 90
                });
            }

            // Command sender
            
            const PICO_HOST = location.hostname === '' ? 'http://pico.local' : '';

            function sendCommand(cmd) {
                // Build a query string: /move?x=13&y=-44   or   /shoot
                let url;
                switch (cmd.action) {
                    case 'move':
                        // default to 0 if pan/tilt omitted
                        url = `${PICO_HOST}/move?x=${cmd.pan ?? 0}&y=${cmd.tilt ?? 0}`;
                        break;
                    case 'center':
                        url = `${PICO_HOST}/center`;
                        break;
                    case 'panorama':
                        url = `${PICO_HOST}/panorama?shots=${cmd.num_shots}&span=${cmd.span_angle}`;
                        break;
                    case 'shoot':
                        url = `${PICO_HOST}/shoot`;
                        break;
                    default:
                        console.warn('Unknown action'); return;
                }

                fetch(url)
                    .then(r => r.text())
                    .then(txt => status.textContent = 'Status: ' + txt.trim())
                    .catch(err => status.textContent = 'Error: ' + err);
            }
            </script>
        </body>
        </html>
    """
    return html
    
# def webpage():
#     """
#     Returns a string containing the HTML for the main webpage.
#     This webpage allows the user to control the robot's servos using
#     two range sliders. The user can set the servo number and angle.
# 
#     The webpage also has a "Move" button that sends a GET request to the
#     server with the servo number and angle. The "Stop" button sends a
#     request to stop the servos.
# 
#     The HTML is returned as a string so that it can be used as the
#     response to an HTTP request.
#     """
#     html = """
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <title>Servo Control</title>
#         </head>
#         <body>
#             <center><b>
#             <form action="/move">
#                 <div>
#                     <label for="leftSlider">Servo Number:</label>
#                     <input type="range" id="leftSlider" name="servo" list="markersNum" min="1" max="4" value="1" 
#                     oninput="document.getElementById('leftValue').innerText = this.value">
#                     <p id="leftValue">1</p>
#                 </div>
#                 <div>
#                     <label for="rightSlider">Servo Angle:</label>
#                     <input type="range" id="rightSlider" name="angle" list="markers" min="0" max="180" value="90" 
#                     oninput="document.getElementById('rightValue').innerText = this.value">
#                     <p id="rightValue">90</p>
#                 </div>
#                 <datalist id="markers">
#                     <option value="0"></option>
#                     <option value="20"></option>
#                     <option value="40"></option>
#                     <option value="60"></option>
#                     <option value="80"></option>
#                     <option value="100"></option>
#                     <option value="120"></option>
#                     <option value="140"></option>
#                     <option value="160"></option>
#                     <option value="180"></option>
#                 </datalist>
#                 <datalist id="markersNum">
#                     <option value="1"></option>
#                     <option value="2"></option>
#                     <option value="3"></option>
#                     <option value="4"></option>
#                 </datalist>
#                 <input type="submit" value="Move" style="height:120px; width:120px" />
#             </form>
#             <form action="/stop">
#                 <input type="submit" value="Stop" style="height:120px; width:120px" />
#             </form>
#         </body>
#         </html>
#     """
#     return html
def serve(connection, servo):
    while True:
        try:
            client = connection.accept()[0]
            request = client.recv(1024).decode('utf-8')
            if not request:
                continue
            print(f"Request: {request}")

            path = request.split(' ')[1]
            
            if path.startswith('/move'):
                if '?' in path:
                    params = path.split('?')[1].split('&')
                    x = int(params[0].split('=')[1])
                    y = int(params[1].split('=')[1])

                    # Map x and y to specific servo movements
                    servo_x_angle = (x + 100) * 90 // 100  # Normalize to 0-180
                    servo_y_angle = (y + 100) * 90 // 100  # Normalize to 0-180
                    
                    print(f"Setting Servo 1 to {servo_x_angle} and Servo 2 to {servo_y_angle}")
                    servo.servo(1, servo_x_angle)
                    servo.servo(2, servo_y_angle)
# 
#             if path.startswith('/move'):
#                 if '?' in path:
#                     params = path.split('?')[1].split('&')
#                     x = int(params[0].split('=')[1])
#                     y = int(params[1].split('=')[1])
# 
#                     # Map normalized joystick values (-100 to 100) to servo angles (0 to 180)
#                     target_x_angle = int((x + 100) * 180 / 200)  # Normalize to 0-180
#                     target_y_angle = int((y + 100) * 180 / 200)  # Normalize to 0-180
# 
# #                     print(f"Moving Servo 1 to {target_x_angle} and Servo 2 to {target_y_angle} smoothly")
#                     
#                     # Use smooth_move to transition the servos
#                     servo.smooth_move(1, 90, target_x_angle, step=1, delay=0.02)  # Smooth move for Servo 1
#                     servo.smooth_move(2, 90, target_y_angle, step=1, delay=0.02)  # Smooth move for Servo 2
                    
            elif path.startswith('/stop'):
                print("Stopping servos")
                servo.release()

            html = webpage()
            client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
            client.send(html)
        except Exception as e:
            print(f"Error in serve loop: {e}")
        finally:
            client.close()

# def serve(connection, servo):
#     while True:
#         try:
#             client = connection.accept()[0]
#             request = client.recv(1024).decode('utf-8')
#             if not request:
#                 continue
#             print(f"Request: {request}")
# 
#             path = request.split(' ')[1]
# 
#             if path.startswith('/move'):
#                 if '?' in path:
#                     params = path.split('?')[1].split('&')
#                     x = int(params[0].split('=')[1])
#                     y = int(params[1].split('=')[1])
#                     
#                     # Map normalized joystick values (-100 to 100) to servo angles (0 to 180)
#                     servo_x_angle = int((x + 100) * 180 / 200)  # Normalize to 0-180
#                     servo_y_angle = int((y + 100) * 180 / 200)  # Normalize to 0-180
#                     
#                     print(f"Setting Servo 1 to {servo_x_angle} and Servo 2 to {servo_y_angle}")
#                     servo.servo(1, servo_x_angle)
#                     servo.servo(2, servo_y_angle)
#             elif path.startswith('/stop'):
#                 print("Stopping servos")
#                 servo.release()
# 
#             html = webpage()
#             client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
#             client.send(html)
#         except Exception as e:
#             print(f"Error in serve loop: {e}")
#         finally:
#             client.close()

# def serve(connection, servo):
#     while True:
#         try:
#             client = connection.accept()[0]
#             request = client.recv(1024).decode('utf-8')
#             if not request:
#                 continue
#             print(f"Request: {request}")
# 
#             path = request.split(' ')[1]
# 
#             if path.startswith('/move'):
#                 if '?' in path:
#                     params = path.split('?')[1].split('&')
#                     x = int(params[0].split('=')[1])
#                     y = int(params[1].split('=')[1])
# 
#                     # Map x and y to specific servo movements
#                     servo_x_angle = (x + 100) * 90 // 100  # Normalize to 0-180
#                     servo_y_angle = (y + 100) * 90 // 100  # Normalize to 0-180
#                     
#                     print(f"Setting Servo 1 to {servo_x_angle} and Servo 2 to {servo_y_angle}")
#                     servo.servo(1, servo_x_angle)
#                     servo.servo(2, servo_y_angle)
#             elif path.startswith('/stop'):
#                 print("Stopping servos")
#                 servo.release()
# 
#             html = webpage()
#             client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
#             client.send(html)
#         except Exception as e:
#             print(f"Error in serve loop: {e}")
#         finally:
#             client.close()

# def serve(connection, servo):
#     while True:
#         try:
#             client = connection.accept()[0]
#             request = client.recv(1024).decode('utf-8')
#             if not request:
#                 continue
#             print(f"Request: {request}")
# 
#             path = request.split(' ')[1]
# 
#             if path.startswith('/move'):
#                 if '?' in path:
#                     params = path.split('?')[1].split('&')
#                     servo_num = int(params[0].split('=')[1])
#                     angle = int(params[1].split('=')[1])
#                     print(f"Moving servo {servo_num} to angle {angle}")
#                     servo.servo(servo_num, angle)
#             elif path.startswith('/stop'):
#                 print("Stopping servos")
#                 servo.release()
# 
#             html = webpage()
#             client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
#             client.send(html)
#         except Exception as e:
#             print(f"Error in serve loop: {e}")
#         finally:
#             client.close()

def main():
    servo = ServoController()
    servo.servo(4, 90)  # Initial positions for the servos
    servo.servo(3, 90)
    servo.servo(2, 180)
    servo.servo(1, 90)
    try:
        ip, wlan = connect()
        connection = open_socket(ip)
        serve(connection, servo)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'connection' in locals():
            connection.close()
        if 'wlan' in locals():
            wlan.disconnect()
        servo.release()
        print("Resetting in 5 seconds...")
        sleep(5)
        import machine
        machine.reset()

if __name__ == "__main__":
    main()
