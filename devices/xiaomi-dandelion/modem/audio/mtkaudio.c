/*
 * mtkaudio: carica l'HAL audio MediaTek di MIUI (audio.primary.mt6765.so) con libhardware
 * e lo comanda da una piccola shell su stdin, senza audioserver né binder.
 * Gira dentro il contenitore (bionic a 32 bit, linker /system/bin/linker).
 *
 * Comandi (uno per riga):
 *   mode <n>            set_mode: 0 normale, 2 in chiamata, 3 VoIP
 *   param <k=v;...>     set_parameters del dispositivo
 *   get <chiavi>        get_parameters del dispositivo
 *   vol <0..1>          set_voice_volume
 *   mute <0|1>          set_mic_mute
 *   open <dev> <flags> <rate> [canali]   apre lo stream di uscita (dev e flags in esadecimale)
 *   oparam <k=v;...>    set_parameters dello stream di uscita
 *   play <file.raw>     scrive PCM 16 bit sullo stream di uscita
 *   close               chiude lo stream di uscita
 *   sleep <s>
 *   quit
 * Costruzione: vedi build.sh
 */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

typedef long ssize_t;
typedef struct FILE FILE;
extern FILE *stdin, *stdout;
int printf(const char *, ...);
int fflush(FILE *);
char *fgets(char *, int, FILE *);
int strncmp(const char *, const char *, size_t);
size_t strlen(const char *);
unsigned long strtoul(const char *, char **, int);
double strtod(const char *, char **);
int open(const char *, int, ...);
ssize_t read(int, void *, size_t);
int close(int);
unsigned int sleep(unsigned int);
int usleep(unsigned int);
void free(void *);
int setvbuf(FILE *, char *, int, size_t);

/* ---- libhardware (Android 10, 32 bit) ---- */
struct hw_module_t;
struct hw_device_t;
struct hw_module_methods_t {
	int (*open)(const struct hw_module_t *, const char *, struct hw_device_t **);
};
struct hw_module_t {
	uint32_t tag;
	uint16_t module_api_version, hal_api_version;
	const char *id, *name, *author;
	struct hw_module_methods_t *methods;
	void *dso;
	uint32_t reserved[32 - 7];
};
struct hw_device_t {
	uint32_t tag, version;
	struct hw_module_t *module;
	uint32_t reserved[12];
	int (*close)(struct hw_device_t *);
};
int hw_get_module_by_class(const char *, const char *, const struct hw_module_t **);

/* ---- audio.h ---- */
typedef struct {
	uint16_t version, size;
	uint32_t sample_rate, channel_mask, format, stream_type, bit_rate;
	int64_t duration_us;
	bool has_video, is_streaming;
	uint32_t bit_width, offload_buffer_size, usage;
} __attribute__((aligned(8))) audio_offload_info_t;
struct audio_config {
	uint32_t sample_rate, channel_mask, format;
	audio_offload_info_t offload_info;
	uint32_t frame_count;
};
struct audio_stream {
	uint32_t (*get_sample_rate)(const struct audio_stream *);
	int (*set_sample_rate)(struct audio_stream *, uint32_t);
	size_t (*get_buffer_size)(const struct audio_stream *);
	uint32_t (*get_channels)(const struct audio_stream *);
	uint32_t (*get_format)(const struct audio_stream *);
	int (*set_format)(struct audio_stream *, uint32_t);
	int (*standby)(struct audio_stream *);
	int (*dump)(const struct audio_stream *, int);
	uint32_t (*get_device)(const struct audio_stream *);
	int (*set_device)(struct audio_stream *, uint32_t);
	int (*set_parameters)(struct audio_stream *, const char *);
	char *(*get_parameters)(const struct audio_stream *, const char *);
	int (*add_audio_effect)(const struct audio_stream *, void *);
	int (*remove_audio_effect)(const struct audio_stream *, void *);
};
struct audio_stream_out {
	struct audio_stream common;
	uint32_t (*get_latency)(const struct audio_stream_out *);
	int (*set_volume)(struct audio_stream_out *, float, float);
	ssize_t (*write)(struct audio_stream_out *, const void *, size_t);
};
struct audio_hw_device {
	struct hw_device_t common;
	uint32_t (*get_supported_devices)(const struct audio_hw_device *);
	int (*init_check)(const struct audio_hw_device *);
	int (*set_voice_volume)(struct audio_hw_device *, float);
	int (*set_master_volume)(struct audio_hw_device *, float);
	int (*get_master_volume)(struct audio_hw_device *, float *);
	int (*set_mode)(struct audio_hw_device *, int);
	int (*set_mic_mute)(struct audio_hw_device *, bool);
	int (*get_mic_mute)(const struct audio_hw_device *, bool *);
	int (*set_parameters)(struct audio_hw_device *, const char *);
	char *(*get_parameters)(const struct audio_hw_device *, const char *);
	size_t (*get_input_buffer_size)(const struct audio_hw_device *, const struct audio_config *);
	int (*open_output_stream)(struct audio_hw_device *, int handle, uint32_t devices,
				  uint32_t flags, struct audio_config *, struct audio_stream_out **,
				  const char *address);
	void (*close_output_stream)(struct audio_hw_device *, struct audio_stream_out *);
};

/* ---- avvio senza crtbegin: bionic __libc_init ---- */
struct structors { void (**preinit)(void); void (**init)(void); void (**fini)(void); };
static const struct structors no_structors = { 0, 0, 0 };
__attribute__((noreturn)) void __libc_init(void *, void (*)(void), int (*)(int, char **, char **),
					   const struct structors *);
int main(int, char **, char **);
__attribute__((used, noreturn)) void start_c(void *sp)
{
	__libc_init(sp, 0, main, &no_structors);
}
__attribute__((naked, noreturn)) void _start(void)
{
	__asm__ volatile("mov r0, sp\n\tb start_c\n");
}

/* ---- shell ---- */
static struct audio_hw_device *dev;
static struct audio_stream_out *out;

static char *arg(char *s)
{
	while (*s && *s != ' ') s++;
	while (*s == ' ') s++;
	return s;
}

int main(int argc, char **argv, char **envp)
{
	const struct hw_module_t *mod;
	char line[1024];
	int r;

	setvbuf(stdout, 0, 2 /* _IONBF */, 0);
	r = hw_get_module_by_class("audio", "primary", &mod);
	printf("hw_get_module: %d\n", r);
	if (r) return 1;
	printf("modulo: %s (%s) api %x\n", mod->name, mod->author, mod->module_api_version);
	r = mod->methods->open(mod, "audio_hw_if", (struct hw_device_t **)&dev);
	printf("open: %d versione %x\n", r, r ? 0 : dev->common.version);
	if (r) return 1;
	printf("init_check: %d\n", dev->init_check(dev));
	printf("pronto\n");

	while (fgets(line, sizeof line, stdin)) {
		size_t n = strlen(line);
		while (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = 0;
		char *a = arg(line);
		if (!strncmp(line, "mode ", 5)) {
			printf("set_mode: %d\n", dev->set_mode(dev, (int)strtoul(a, 0, 0)));
		} else if (!strncmp(line, "param ", 6)) {
			printf("set_parameters: %d\n", dev->set_parameters(dev, a));
		} else if (!strncmp(line, "get ", 4)) {
			char *v = dev->get_parameters(dev, a);
			printf("get_parameters: %s\n", v ? v : "(null)");
			free(v);
		} else if (!strncmp(line, "vol ", 4)) {
			printf("set_voice_volume: %d\n", dev->set_voice_volume(dev, (float)strtod(a, 0)));
		} else if (!strncmp(line, "mute ", 5)) {
			printf("set_mic_mute: %d\n", dev->set_mic_mute(dev, strtoul(a, 0, 0) != 0));
		} else if (!strncmp(line, "open ", 5)) {
			char *p = a;
			uint32_t d = strtoul(p, &p, 16), f = strtoul(p, &p, 16);
			uint32_t rate = strtoul(p, &p, 10), ch = strtoul(p, &p, 10);
			struct audio_config c = { 0 };
			c.sample_rate = rate ? rate : 48000;
			c.channel_mask = ch == 1 ? 0x1 : 0x3; /* MONO / STEREO */
			c.format = 0x1; /* PCM_16_BIT */
			c.offload_info.version = 0x0201;
			c.offload_info.size = sizeof c.offload_info;
			if (out) { dev->close_output_stream(dev, out); out = 0; }
			r = dev->open_output_stream(dev, 13, d, f, &c, &out, "");
			printf("open_output_stream: %d rate %u ch %x fmt %x\n", r, c.sample_rate,
			       c.channel_mask, c.format);
			if (r) out = 0;
			else printf("buffer %u byte, latenza %u ms\n",
				    (unsigned)out->common.get_buffer_size(&out->common),
				    out->get_latency(out));
		} else if (!strncmp(line, "oparam ", 7)) {
			printf("stream set_parameters: %d\n",
			       out ? out->common.set_parameters(&out->common, a) : -1);
		} else if (!strncmp(line, "play ", 5)) {
			int fd = open(a, 0);
			static char buf[8192];
			ssize_t k, tot = 0;
			if (fd < 0 || !out) { printf("play: errore\n"); continue; }
			size_t bs = out->common.get_buffer_size(&out->common);
			if (bs > sizeof buf) bs = sizeof buf;
			while ((k = read(fd, buf, bs)) > 0) {
				ssize_t w = out->write(out, buf, k);
				if (w < 0) { printf("write: %d\n", (int)w); break; }
				tot += w;
			}
			close(fd);
			printf("play: %d byte\n", (int)tot);
		} else if (!strncmp(line, "close", 5)) {
			if (out) dev->close_output_stream(dev, out);
			out = 0;
			printf("chiuso\n");
		} else if (!strncmp(line, "sleep ", 6)) {
			usleep((unsigned)(strtod(a, 0) * 1e6));
			printf("ok\n");
		} else if (!strncmp(line, "quit", 4)) {
			break;
		} else if (n) {
			printf("comando sconosciuto: %s\n", line);
		}
	}
	if (out) dev->close_output_stream(dev, out);
	dev->common.close(&dev->common);
	return 0;
}
