# in widgets/camera_widget.py
import dearpygui.dearpygui as dpg
import gphoto2 as gp
import logging
import threading
import queue
import tempfile
import os

from .base_widget import BaseWidget

# Set up a logger specific to this widget for clear debugging
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

class CamControlWidget(BaseWidget):
    def __init__(self, widget_type: str, config: dict, layout_manager, app_state):
        super().__init__(widget_type, config, layout_manager, app_state)
        layout_manager.updating_widgets.append("CamControlWidget")

        # A dictionary to map user-friendly camera names to technical port strings
        self.camera_map = {}

        # Queues for communicating with the worker thread
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()

        # Start the background worker thread. It's a daemon so it exits with the app.
        self.worker_thread = threading.Thread(target=self._camera_worker, daemon=True)
        self.worker_thread.start()
        
        self.command_queue.put(('DETECT', None))

    def create(self):
        if dpg.does_item_exist(self.window_tag): return

        with dpg.window(label="Camera Control", tag=self.window_tag, on_close=self._on_window_close, width=320, height=160):
            
            # This group contains all controls visible when disconnected
            with dpg.group(tag=f"connection_group_{self.widget_type}") as self.connection_group_tag:
                dpg.add_button(label="Detect Cameras", callback=lambda: self.command_queue.put(('DETECT', None)), width=-1)
                with dpg.group(horizontal=True):
                    self.camera_combo_tag = dpg.add_combo(label="Camera", items=[], width=-115)
                    
                    def connect_callback():
                        selected_name = dpg.get_value(self.camera_combo_tag)
                        if selected_name and selected_name in self.camera_map:
                            port = self.camera_map[selected_name]
                            self.command_queue.put(('CONNECT', port))
                        else:
                            logger.warning("No camera selected to connect to.")
                    
                    self.connect_button = dpg.add_button(label="Connect", callback=connect_callback)
            
            # This button is only visible when connected
            self.disconnect_button_tag = dpg.add_button(
                label="Disconnect", 
                callback=lambda: self.command_queue.put(('DISCONNECT', None)), 
                show=False,
                width=-1
            )
            
            self.status_text_tag = dpg.add_text("Status: Disconnected")

            # This is only visible when connected
            with dpg.group(tag=f"connected_group_{self.widget_type}", show=False) as self.connected_group_tag:
                dpg.add_separator()

                dpg.add_button(label="Capture Image", width=-1, callback=lambda: self.command_queue.put(('CAPTURE', None)))
                self.capture_path_text_tag = dpg.add_text("Last Capture: None")

                dpg.add_separator()
                
                dpg.add_button(label="Refresh Config", width=-1, callback=lambda: self.command_queue.put(('GET_CONFIG', None)))
                # A child window makes the table scrollable
                with dpg.child_window(height=-1):
                    # The table will be populated dynamically
                    self.config_table_tag = dpg.add_table(header_row=True, borders_innerV=True)
                    dpg.add_table_column(parent=self.config_table_tag, label="Setting")
                    dpg.add_table_column(parent=self.config_table_tag, label="Value", width_fixed=True)

    def update(self):
        try:
            # Check for a result from the worker thread without blocking
            result_type, data = self.result_queue.get_nowait()

            if result_type == 'STATUS':
                dpg.set_value(self.status_text_tag, f"Status: {data}")

            elif result_type == 'CAMERAS_DETECTED':
                # data is a list of (name, port) tuples
                self.camera_map = {name: port for name, port in data}
                camera_names = list(self.camera_map.keys())
                dpg.configure_item(self.camera_combo_tag, items=camera_names)
                if camera_names:
                    dpg.set_value(self.camera_combo_tag, camera_names[0])

            elif result_type == 'CONNECTED' and data is True:
                # Hide connection controls and show the disconnect button
                dpg.configure_item(self.connection_group_tag, show=False)
                dpg.configure_item(self.disconnect_button_tag, show=True)
                dpg.configure_item(self.connected_group_tag, show=True)
                # Automatically fetch config on connect
                self.command_queue.put(('GET_CONFIG', None))

            elif result_type == 'DISCONNECTED' and data is True:
                # Hide disconnect button and show connection controls
                dpg.configure_item(self.connection_group_tag, show=True)
                dpg.configure_item(self.disconnect_button_tag, show=False)
                dpg.configure_item(self.connected_group_tag, show=False)

            elif result_type == 'CONFIG_DATA':
                # Clear any old settings from the table
                dpg.delete_item(self.config_table_tag, children_only=True)
                # Re-add columns because they were deleted
                dpg.add_table_column(parent=self.config_table_tag, label="Setting")
                dpg.add_table_column(parent=self.config_table_tag, label="Value", width_fixed=True)

                # Dynamically create a UI element for each setting
                for key, item_data in data.items():
                    # But only if it is one of the following fields:
                    if item_data['label'] not in [
                        "ISO Speed",  "Auto ISO", "WhiteBalance", "Focus Mode", 
                        "Aperture", "F-Number", "Image Quality", "Focus Mode 2",
                        "Shutter Speed", "Picture Style", "Image Format", "Shutter Speed 2"
                        ]:
                        continue
                    with dpg.table_row(parent=self.config_table_tag):
                        dpg.add_text(item_data['label'])
                        
                        # Create a combo box for settings with choices
                        if item_data['type'] in [gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU] and item_data['choices']:
                            dpg.add_combo(items=item_data['choices'], default_value=item_data['value'], width=200,
                                          callback=lambda s, a, u: self.command_queue.put(('SET_CONFIG', (u, a))),
                                          user_data=key)
                        # Otherwise, create a simple text input
                        else:
                            dpg.add_input_text(default_value=str(item_data['value']), width=200, on_enter=True,
                                               callback=lambda s, a, u: self.command_queue.put(('SET_CONFIG', (u, a))),
                                               user_data=key)
                            
            elif result_type == 'CAPTURE_COMPLETE':
                # The 'data' variable contains the file path sent from the worker
                file_path = data
                self.global_state.dispatch("NEW_IMAGE_CAPTURED", image_path=file_path)
                dpg.set_value(self.capture_path_text_tag, f"Last Capture: {file_path}")

        except queue.Empty:
            # This is expected when there are no new results from the worker
            pass

    def _camera_worker(self):
        camera = None
        logger.info("Camera worker thread started.")

        while True:
            try:
                command, args = self.command_queue.get()
                logger.info(f"Camera worker received command: {command}")

                if command == 'DETECT':
                    try:
                        # Autodetect returns a list of (name, port) tuples
                        camera_list = list(gp.Camera.autodetect())
                        if not camera_list:
                            self.result_queue.put(('STATUS', 'No cameras found.'))
                            self.result_queue.put(('CAMERAS_DETECTED', []))
                            continue
                        
                        self.result_queue.put(('CAMERAS_DETECTED', camera_list))
                        self.result_queue.put(('STATUS', f'Detected {len(camera_list)} camera(s).'))
                    except Exception as e:
                        logger.error(f"Error during camera detection: {e}")
                        self.result_queue.put(('STATUS', 'Error during detection.'))

                elif command == 'CONNECT':
                    if camera is not None:
                        self.result_queue.put(('STATUS', 'A camera is already connected.'))
                        continue
                    
                    port = args
                    if not port:
                        self.result_queue.put(('STATUS', 'No camera port selected.'))
                        continue
                        
                    try:
                        camera = gp.Camera()
                        port_info_list = gp.PortInfoList(); port_info_list.load()
                        port_index = port_info_list.lookup_path(port)
                        camera.set_port_info(port_info_list[port_index])
                        
                        camera.init()
                        self.result_queue.put(('STATUS', f"Connected successfully!"))
                        self.result_queue.put(('CONNECTED', True))
                    except gp.GPhoto2Error as ex:
                        camera = None # Ensure camera is None on failure
                        logger.error(f"GPhoto2 Error on connect: {ex}")
                        self.result_queue.put(('STATUS', f"Error: {ex}"))
                        self.result_queue.put(('CONNECTED', False))

                elif command == 'DISCONNECT':
                    if camera:
                        try:
                            camera.exit()
                            camera = None # Critical to update state
                            self.result_queue.put(('STATUS', 'Disconnected.'))
                            self.result_queue.put(('DISCONNECTED', True))
                        except gp.GPhoto2Error as ex:
                            logger.error(f"Error on disconnect: {ex}")
                            self.result_queue.put(('STATUS', f"Error on disconnect: {ex}"))
                    else:
                        self.result_queue.put(('STATUS', 'Already disconnected.'))

                elif command == 'GET_CONFIG':
                    if camera is None:
                        self.result_queue.put(('STATUS', 'Not connected.'))
                        continue
                    try:
                        config_dict = self._get_config_as_dict(camera)
                        self.result_queue.put(('CONFIG_DATA', config_dict))
                        self.result_queue.put(('STATUS', 'Configuration loaded.'))
                    except Exception as e:
                        logger.error(f"Could not get camera config: {e}")
                        self.result_queue.put(('STATUS', f"Error getting config: {e}"))

                elif command == 'SET_CONFIG':
                    if camera is None: continue
                    key, value = args
                    try:
                        config = camera.get_config()
                        widget = config.get_child_by_name(key)
                        
                        # Check the widget type to set the value correctly
                        widget_type = widget.get_type()
                        if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                            # For choice-based widgets, value is a string
                            widget.set_value(str(value))
                        elif widget_type == gp.GP_WIDGET_TEXT:
                            widget.set_value(str(value))
                        # Add more type checks if needed (e.g., for integers, floats)

                        camera.set_config(config)
                        self.result_queue.put(('STATUS', f"Set '{key}' to '{value}'"))
                    except gp.GPhoto2Error as e:
                        logger.error(f"Failed to set config '{key}': {e}")
                        self.result_queue.put(('STATUS', f"Error setting '{key}': {e}"))

                elif command == 'CAPTURE':
                    if camera is None:
                        self.result_queue.put(('STATUS', 'Not connected.'))
                        continue

                    self.result_queue.put(('STATUS', 'Capturing...'))
                    try:
                        # This captures the image to the camera's internal RAM
                        file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                        logger.info(f"Image captured on camera: {file_path.folder}{file_path.name}")
                        
                        # Define a destination on the computer in the system's temp directory
                        temp_dir = tempfile.gettempdir()
                        destination_path = os.path.join(temp_dir, f"{file_path.name}")
                        
                        # Download the file from the camera to the destination
                        logger.info(f"Downloading image to: {destination_path}")
                        camera_file = camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
                        camera_file.save(destination_path)
                        
                        # Send the path of the completed file back to the UI
                        self.result_queue.put(('CAPTURE_COMPLETE', destination_path))
                        self.result_queue.put(('STATUS', 'Capture successful!'))

                    except gp.GPhoto2Error as ex:
                        logger.error(f"GPhoto2 Error during capture: {ex}")
                        self.result_queue.put(('STATUS', f'Capture Error: {ex}'))

            except Exception as e:
                # Broad exception to catch any other errors in the worker loop
                logger.error(f"An unexpected exception occurred in the camera worker: {e}")
                self.result_queue.put(('STATUS', f'Worker Error: {e}'))

    def _get_config_as_dict(self, camera):
        """
        Helper function to recursively get all camera configuration values
        and return them as a simplified dictionary.
        """
        config_dict = {}
        # Get the camera's full configuration tree
        config = camera.get_config()
        
        # We're interested in top-level sections like 'capturesettings' and 'imgsettings'
        for section in config.get_children():
            for child in section.get_children():
                # Skip read-only or unreadable widgets
                if child.get_readonly():
                    continue
                
                try:
                    # Store all relevant info for building a UI
                    config_dict[child.get_name()] = {
                        'label': child.get_label(),
                        'type': child.get_type(),
                        'value': child.get_value(),
                        'choices': list(child.get_choices()) if child.get_type() in [gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU] else None
                    }
                except gp.GPhoto2Error:
                    # Some settings might not be available depending on camera mode
                    continue
        return config_dict