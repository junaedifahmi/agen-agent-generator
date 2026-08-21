# agen-agent-generator

**Agen** adalah agen elicitor berbasis Agno. Agen berdialog dengan pengguna
bisnis memakai bahasa bisnis sehari-hari, memetakan jawaban mereka ke sebuah
feature model Software Product Line Engineering (SPLE) yang sudah tetap, lalu
menghasilkan spesifikasi YAML teknis yang tervalidasi. Spesifikasi itulah yang
kemudian dipakai oleh generator (yang diasumsikan sudah ada) untuk membangun
chatbot yang siap dijalankan.

## Implementasi dan desain sistem

Sistem ini dirancang di atas satu prinsip: **model bahasa dipakai untuk
menerjemahkan, bukan untuk mengingat maupun untuk mengambil keputusan
berisiko.** Secara arsitektur, Agen dibagi menjadi tiga lapisan yang sengaja
dipisah. Lapisan *domain* (`agent/feature_model.py`) memegang feature model SPLE
sebagai model Pydantic — inilah satu-satunya sumber kebenaran tentang varian apa
saja yang boleh dipilih, sehingga spesifikasi yang tidak valid gagal di tahap
validasi, bukan di tahap generasi. Lapisan *percakapan* (`agent/elicitor.py`,
`agent/tools.py`, `agent/state.py`) menjalankan elicitation: setiap kali pengguna
menjawab, Agen langsung memanggil tool yang sesuai untuk mencatat jawaban itu ke
dalam `session_state` yang terstruktur, dan state tersebut disuntikkan kembali ke
dalam system prompt pada giliran berikutnya lewat placeholder `{business_name}`.
Pendekatan ini menggantikan cara lama yang membiarkan model menyimpulkan sendiri
"apa yang sudah dibahas" dari transkrip — cara lama itu terbukti melenceng pada
percakapan panjang dan membuat Agen mengulang pertanyaan yang sudah dijawab.
Karena state tercatat eksplisit, spesifikasi akhir pun dibangun secara
deterministik oleh `build_spec_from_state()`, bukan dengan meminta model merangkum
ulang percakapan (yang berisiko berhalusinasi). Lapisan *kendali* menutup rantai
ini: satu-satunya aksi yang berdampak nyata, yaitu `generate_chatbot_now`,
ditandai `@approval` + `requires_confirmation=True` sehingga Agno menjeda run dan
menulis catatan approval ke database alih-alih mengeksekusinya — keputusan
akhirnya dipegang manusia melalui antarmuka terpisah, bukan oleh penilaian model.
Di sisi penyajian, seluruh lapisan HTTP memakai `AgentOS` bawaan Agno
(`agno.os.AgentOS`) daripada API buatan sendiri, sehingga protokol
run/pause/continue beserta API approval lintas-sesi datang langsung dari framework
dan tidak perlu diduplikasi.

## Feature model

Setiap chatbot yang dihasilkan disusun dari empat area fitur wajib
(lihat `agent/feature_model.py`):

- **Connector** (pilih satu): WhatsApp, WebApp, atau Telegram — hanya
  kanalnya saja. Kredensial dan detail koneksi lain dikonfigurasi di
  dashboard setelah generasi, bukan digali oleh Agen.
- **Knowledge base**: apakah chatbot memilikinya, dan jika ya, apakah
  berbasis vector atau API — hanya *mode* pencariannya. Dokumen mana,
  vector database mana, API mana, dan seterusnya adalah detail implementasi
  yang sudah ditetapkan SPLE dan dikonfigurasi lewat dashboard, bukan hal
  yang ditanyakan Agen.
- **Skills**: satu atau lebih kemampuan yang harus dimiliki chatbot
  (misalnya menjawab FAQ, menerima pesanan, mengecek status pesanan),
  masing-masing dengan nama dan deskripsi dalam bahasa awam.
- **Persona**: system prompt, gaya bicara, bahasa, dan aturan eskalasi.

Tugas Agen adalah menentukan *varian mana* dari tiap fitur yang diinginkan
bisnis melalui percakapan bebas — bukan mengumpulkan detail implementasi,
dan bukan menulis YAML secara manual.

## Persiapan

```bash
uv sync
cp .env.example .env   # lalu isi OPENROUTER_API_KEY
```

## Menjalankan

```bash
uv run main.py
```

Ngobrol dengan Agen tentang chatbot yang Anda inginkan. Setelah semua
kebutuhan untuk connector, knowledge base, skills, dan persona terkumpul,
Agen akan merangkum apa yang sudah dikumpulkannya dan menanyakan apakah
chatbot boleh digenerate sekarang. Jika Anda setuju, Agen menulis
spesifikasi ke `specs/<business>-<timestamp>.yaml` lalu menyerahkannya ke
`generate_chatbot()` (saat ini masih stub di `agent/generator_stub.py` —
ganti dengan implementasi sebenarnya ketika sudah tersedia).

## Konfirmasi human-in-the-loop

Menggenerate chatbot adalah satu-satunya aksi berdampak nyata di seluruh
alur ini, jadi aksi tersebut dijaga oleh mekanisme konfirmasi tool milik
Agno, bukan dipercayakan pada penilaian model. `generate_chatbot_now`
(`agent/generation_tool.py`) didaftarkan dengan `requires_confirmation=True`;
begitu Agen mencoba memanggilnya, `agent.run()` kembali dalam keadaan
ter-pause alih-alih mengeksekusinya. Fungsi `resolve_pending_confirmations()`
di `main.py` yang menampilkan panggilan tertunda itu dan meminta jawaban
y/n eksplisit sebelum melanjutkan dengan `agent.continue_run()` — sehingga
sekalipun Agen salah menilai bahwa "percakapan terdengar sudah selesai",
tidak ada apa pun yang terjadi sampai Anda menyetujui panggilan tersebut.

### Mencobanya sebagai dua antarmuka terpisah

`main.py` mendemonstrasikan gerbang ini dalam satu terminal, dan itu membuat
intinya mudah terlewat: orang yang menyetujui belum tentu orang yang sedang
mengobrol. `demo/` membuat pemisahan itu menjadi nyata dengan memakai lapisan
penyajian HTTP milik Agno sendiri, `AgentOS` (`agno.os.AgentOS`) — bukan API
buatan sendiri. `demo/server.py` membungkus Agen dengan
`AgentOS(agents=[agent], db=agent.db)` dan menyajikan dua halaman statis di
atas protokol REST aslinya:

- `/` — halaman chat, berbicara dengan Agen lewat `POST /agents/agen/runs`.
  **Semua balasan di halaman ini berasal dari agen sungguhan.**
- `/review` — halaman peninjau yang benar-benar terpisah, berbicara dengan
  **approvals API** bawaan Agno yang tersimpan di database (`GET /approvals`,
  `POST /approvals/{id}/resolve`). Karena `generate_chatbot_now` ditandai
  `@approval` (lihat `agent/generation_tool.py`), begitu ia menjeda sebuah run
  Agno menulis catatan approval sungguhan — sehingga halaman review bisa
  mendaftar setiap permintaan "generate sekarang?" yang tertunda dari *semua*
  sesi chat hanya dengan satu `GET /approvals?status=pending`, tanpa perlu
  mengetahui session id sebelumnya.

```bash
uv run uvicorn demo.server:app --reload
```

Lalu buka dua tab browser:

- `http://127.0.0.1:8000/` — mengobrol dengan Agen sebagai pengguna bisnis.
- `http://127.0.0.1:8000/review` — layar peninjau. Halaman ini memantau
  `GET /approvals` untuk panggilan `generate_chatbot_now` yang tertunda dan
  bisa menyetujui atau menolaknya.

Ngobrollah di sana sampai Agen menawarkan untuk menggenerate dan Anda
menjawab ya; tab chat akan menampilkan "menunggu peninjau manusia" dan terus
memantau run tersebut sampai tidak lagi ter-pause. Tidak ada bagian dari UI
chat yang bisa melewati penantian itu: run tetap berstatus `PAUSED` di sisi
server sampai tab *yang lain* menyelesaikan approval dan memanggil
`.../continue` pada run tersebut — tab chat baru mengetahui hasilnya setelah
itu terjadi.

Catatan soal routing: AgentOS mendaftarkan `GET /` miliknya sendiri (sebuah
endpoint identitas berformat JSON) dan secara bawaan memenangkan setiap
konflik path, sehingga menambahkan `@app.get("/")` pada app yang
dikembalikannya akan diabaikan diam-diam dan `/` menyajikan JSON alih-alih
halaman chat. `demo/server.py` menghindari hal itu dengan membangun route UI
pada FastAPI app-nya sendiri lalu menyerahkannya ke AgentOS sebagai
`base_app=` dengan `on_route_conflict="preserve_base_app"`. Endpoint identitas
AgentOS tetap bisa diakses di `/os`.

### Pratinjau statis: `docs/agen-demo-ui.html`

Terpisah dari yang di atas, dan **tidak terhubung ke agen**:
`docs/agen-demo-ui.html` adalah satu berkas statis yang percakapannya
di-script di dalam browser. Berkas ini hanya untuk memperlihatkan bentuk alur
dua-antarmuka tanpa perlu menjalankan apa pun — untuk screenshot atau
peragaan singkat. Semua balasan di dalamnya sudah ditulis sebelumnya. Untuk
jawaban sungguhan dari Agen, jalankan server di atas.

## Guardrails

Setiap pesan pengguna melewati `agent/guardrails.py` sebelum sampai ke model:

- `PromptInjectionGuardrail` (bawaan Agno) memblokir pola prompt injection
  yang umum.
- `ScopeLockGuardrail` (custom) memblokir upaya mengalihkan Agen dari
  perannya sebagai elicitor atau menimpa instruksinya.

## Struktur berkas

```
agent/
  feature_model.py             # model domain SPLE (Pydantic) -- sumber kebenaran
  state.py                     # bentuk progres elicitation yang dilacak
  tools.py                     # tool yang mencatat jawaban ke session state
  generation_tool.py           # generate_chatbot_now -- tool yang dijaga HITL
  guardrails.py                # guardrail prompt-injection + scope-lock
  elicitor.py                  # konstruksi Agno Agent
  yaml_export.py               # ChatbotSpec -> berkas YAML
  generator_stub.py            # placeholder untuk generate_chatbot() yang sudah ada
  config.py                    # setting dari environment variable
  prompts/
    elicitor_system_prompt.md  # system prompt Agen, bisa diubah tanpa menyentuh kode
main.py                        # loop chat CLI + penanganan konfirmasi
demo/
  server.py                    # app AgentOS: chat + review sebagai dua antarmuka terpisah
  static/chat.html             # halaman chat pengguna bisnis
  static/review.html           # halaman persetujuan peninjau
docs/
  agen-demo-ui.html            # pratinjau statis ber-script -- tidak butuh server
  agen-elicitation-flow.md     # activity diagram
```

System prompt Agen disimpan di `agent/prompts/elicitor_system_prompt.md`,
bukan di dalam Python, supaya bisa ditinjau atau disetel tersendiri. Berkas
itu memuat placeholder bergaya `{business_name}` yang disubstitusi Agno saat
runtime dari session state yang aktif (lihat `agent/state.py`) — itulah yang
membuat Agen tahu apa saja yang sudah terjawab tanpa harus membaca ulang
seluruh percakapan.
