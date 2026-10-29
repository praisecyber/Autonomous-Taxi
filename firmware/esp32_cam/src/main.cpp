// AI Thinker ESP32-CAM CAMERA + READ-ONLY TELEMETRY bench starter.
// No physical movement endpoint. Confirm your module before using this pin map.
#include <Arduino.h>
#include <WiFi.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Copy src/config.example.h to src/secrets.h and configure Wi-Fi and token"
#endif

HardwareSerial relay(1);
httpd_handle_t server = nullptr;
char latest[256] = "{\"state\":\"NO_TELEMETRY\"}";
char line[256];
size_t used = 0;
bool overflowed = false;
uint32_t receivedAt = 0;
portMUX_TYPE telemetryMux = portMUX_INITIALIZER_UNLOCKED;

bool authorized(httpd_req_t *req) {
  char supplied[128];
  if (httpd_req_get_hdr_value_str(req, "X-Device-Token", supplied, sizeof(supplied)) != ESP_OK
      || strcmp(supplied, DEVICE_TOKEN) != 0) {
    httpd_resp_send_err(req, HTTPD_401_UNAUTHORIZED, "Device token required");
    return false;
  }
  return true;
}

esp_err_t capture(httpd_req_t *req) {
  if (!authorized(req)) return ESP_OK;
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Capture failed");
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  esp_err_t result = httpd_resp_send(req, (const char*)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return result;
}

esp_err_t telemetry(httpd_req_t *req) {
  if (!authorized(req)) return ESP_OK;
  char copy[256];
  uint32_t stamp;
  portENTER_CRITICAL(&telemetryMux);
  memcpy(copy, latest, sizeof(copy)); stamp = receivedAt;
  portEXIT_CRITICAL(&telemetryMux);
  char response[460];
  // UART data is NOT parsed or certified by this bench relay.
  // Return it as plain text instead of inserting unvalidated data into JSON.
  snprintf(response, sizeof(response), "mode=bench\nmotion_enabled=false\ntelemetry_age_ms=%lu\nuart_line=%s\n",
           (unsigned long)(stamp ? millis()-stamp : 0), copy);
  httpd_resp_set_type(req, "text/plain");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  return httpd_resp_send(req, response, HTTPD_RESP_USE_STRLEN);
}

esp_err_t stopRequest(httpd_req_t *req) {
  if (!authorized(req)) return ESP_OK;
  if (RELAY_RX_PIN < 0 || RELAY_TX_PIN < 0)
    return httpd_resp_send_err(req, HTTPD_503_SERVICE_UNAVAILABLE, "UART not configured");
  relay.print("STOP\n");
  return httpd_resp_send(req, "Stop requested; physical stop NOT confirmed", HTTPD_RESP_USE_STRLEN);
}

bool startCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0; c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0=5; c.pin_d1=18; c.pin_d2=19; c.pin_d3=21;
  c.pin_d4=36; c.pin_d5=39; c.pin_d6=34; c.pin_d7=35;
  c.pin_xclk=0; c.pin_pclk=22; c.pin_vsync=25; c.pin_href=23;
  c.pin_sccb_sda=26; c.pin_sccb_scl=27;
  c.pin_pwdn=32; c.pin_reset=-1; c.xclk_freq_hz=20000000;
  c.pixel_format=PIXFORMAT_JPEG; c.frame_size=FRAMESIZE_QVGA;
  c.jpeg_quality=14; c.fb_count=1;
  return esp_camera_init(&c)==ESP_OK;
}

void setup() {
  Serial.begin(115200);
  if (RELAY_RX_PIN >= 0 && RELAY_TX_PIN >= 0)
    relay.begin(115200, SERIAL_8N1, RELAY_RX_PIN, RELAY_TX_PIN);
  if (!startCamera()) { Serial.println("Camera init failed; halted"); while(true) delay(1000); }
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t started=millis();
  while(WiFi.status()!=WL_CONNECTED && millis()-started<20000) delay(100);
  if(WiFi.status()!=WL_CONNECTED) { Serial.println("Wi-Fi failed; halted"); while(true) delay(1000); }
  httpd_config_t config=HTTPD_DEFAULT_CONFIG();
  if(httpd_start(&server,&config)!=ESP_OK) return;
  httpd_uri_t image={}; image.uri="/capture"; image.method=HTTP_GET; image.handler=capture;
  httpd_uri_t state={}; state.uri="/telemetry"; state.method=HTTP_GET; state.handler=telemetry;
  httpd_uri_t stop={}; stop.uri="/stop"; stop.method=HTTP_POST; stop.handler=stopRequest;
  httpd_register_uri_handler(server,&image); httpd_register_uri_handler(server,&state);
  httpd_register_uri_handler(server,&stop);
  Serial.print("Bench camera URL: http://"); Serial.println(WiFi.localIP());
}

void loop() {
  // Bound processing per iteration; oversized lines are discarded completely.
  if(RELAY_RX_PIN >= 0 && RELAY_TX_PIN >= 0) {
    for(int n=0;n<64 && relay.available();n++) {
      char ch=(char)relay.read();
      if(ch=='\n') {
        if(!overflowed && used) {
          line[used]='\0';
          portENTER_CRITICAL(&telemetryMux);
          memcpy(latest,line,used+1); receivedAt=millis();
          portEXIT_CRITICAL(&telemetryMux);
        }
        used=0; overflowed=false;
      } else if(ch!='\r') {
        if(used<sizeof(line)-1 && !overflowed) line[used++]=ch;
        else overflowed=true;
      }
    }
  }
  delay(1);
}
