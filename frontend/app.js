/* Yellow loan application — frontend logic.
   The validation here mirrors backend/validators.py. It exists for fast
   feedback only; the backend is the control, since this file can be
   bypassed entirely. */

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];

function readError(payload, status) {
  const detail = payload && payload.detail;

  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : '';
    return field ? `${field}: ${first.msg}` : first.msg;
  }

  return `Something went wrong (HTTP ${status}). Check the server log.`;
}

/* ---------- SA ID helpers (mirror of the Python versions) ---------- */

function luhnCheckDigit(firstTwelve) {
  let total = 0;
  firstTwelve.split('').reverse().forEach((char, position) => {
    let digit = Number(char);
    if (position % 2 === 0) {          // every second digit from the right
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    total += digit;
  });
  return (10 - (total % 10)) % 10;
}

function dateOfBirthFromId(yymmdd) {
  const yy = Number(yymmdd.slice(0, 2));
  const mm = Number(yymmdd.slice(2, 4));
  const dd = Number(yymmdd.slice(4, 6));
  const today = new Date();

  for (const century of [2000, 1900]) {
    const year = century + yy;
    const candidate = new Date(year, mm - 1, dd);
    // JS rolls 31 February over into March — reject that.
    const valid = candidate.getFullYear() === year
      && candidate.getMonth() === mm - 1
      && candidate.getDate() === dd;
    if (valid && candidate <= today) return candidate;
  }
  return null;
}

function parseSaId(idNumber) {
  const cleaned = (idNumber || '').replace(/\s/g, '');
  if (!cleaned) return { error: 'ID number is required.' };
  if (!/^\d+$/.test(cleaned)) return { error: 'ID number must contain digits only.' };
  if (cleaned.length !== 13) return { error: 'ID number must be exactly 13 digits.' };

  const dateOfBirth = dateOfBirthFromId(cleaned.slice(0, 6));
  if (!dateOfBirth) return { error: 'ID number contains an invalid date of birth.' };

  if (cleaned[10] !== '0' && cleaned[10] !== '1') {
    return { error: 'ID number has an invalid citizenship digit.' };
  }
  if (Number(cleaned[12]) !== luhnCheckDigit(cleaned.slice(0, 12))) {
    return { error: 'ID number is not valid. Please check for typos.' };
  }
  return { dateOfBirth, cleaned };
}

function ageOn(dateOfBirth, on = new Date()) {
  let age = on.getFullYear() - dateOfBirth.getFullYear();
  const hadBirthday =
    on.getMonth() > dateOfBirth.getMonth() ||
    (on.getMonth() === dateOfBirth.getMonth() && on.getDate() >= dateOfBirth.getDate());
  return hadBirthday ? age : age - 1;
}

function toIsoDate(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/* ------------------------------ the app ------------------------------ */

const { createApp } = Vue;

createApp({
  data() {
    return {
      step: 1,
      stepLabels: ['You', 'Income', 'Phone', 'Confirm'],
      form: {
        fullName: '',
        idNumber: '',
        dateOfBirth: '',
        monthlyIncome: '',
        document: null,
        phoneId: null,
      },
      errors: {},
      idHint: '',
      phones: [],
      loadingPhones: false,
      submitting: false,
      submitted: false,
      serverError: '',
      result: null,
    };
  },

  computed: {
    chosenPhone() {
      return this.phones.find((p) => p.id === this.form.phoneId) || null;
    },
  },

  methods: {

    /* ---------------- field validation ---------------- */

    validateName() {
      const name = this.form.fullName.trim().replace(/\s+/g, ' ');
      this.form.fullName = name;
      this.errors.fullName = name.length < 2 ? 'Please enter your full name.' : '';
      return !this.errors.fullName;
    },

    validateIdNumber() {
      this.idHint = '';
      const result = parseSaId(this.form.idNumber);

      if (result.error) {
        this.errors.idNumber = result.error;
        return false;
      }

      this.form.idNumber = result.cleaned;
      const age = ageOn(result.dateOfBirth);

      if (age < 18) {
        this.errors.idNumber = 'Applicants must be at least 18 years old.';
        return false;
      }
      if (age > 65) {
        this.errors.idNumber = 'Applicants must be 65 years old or younger.';
        return false;
      }

      this.errors.idNumber = '';
      this.idHint = `Valid ID — born ${toIsoDate(result.dateOfBirth)}, age ${age}.`;
      return true;
    },

    validateDateOfBirth() {
      if (!this.form.dateOfBirth) {
        this.errors.dateOfBirth = 'Date of birth is required.';
        return false;
      }

      const fromId = parseSaId(this.form.idNumber);
      if (!fromId.error && toIsoDate(fromId.dateOfBirth) !== this.form.dateOfBirth) {
        this.errors.dateOfBirth = 'This does not match the date in your ID number.';
        return false;
      }

      // Append a time so the browser parses this as local, not UTC.
      const age = ageOn(new Date(`${this.form.dateOfBirth}T00:00:00`));
      if (age < 18) {
        this.errors.dateOfBirth = 'Applicants must be at least 18 years old.';
        return false;
      }
      if (age > 65) {
        this.errors.dateOfBirth = 'Applicants must be 65 years old or younger.';
        return false;
      }

      this.errors.dateOfBirth = '';
      return true;
    },

    validateIncome() {
      const value = Number(this.form.monthlyIncome);
      if (!this.form.monthlyIncome || Number.isNaN(value) || value <= 0) {
        this.errors.monthlyIncome = 'Enter your monthly income.';
        return false;
      }
      this.errors.monthlyIncome = '';
      return true;
    },

    validateDocument() {
      if (!this.form.document) {
        this.errors.document = 'Please attach proof of income.';
        return false;
      }
      this.errors.document = '';
      return true;
    },

    onFileChange(event) {
      const file = event.target.files[0];
      if (!file) return;

      if (!ALLOWED_TYPES.includes(file.type)) {
        this.form.document = null;
        this.errors.document = 'Upload a PDF, JPG or PNG.';
        return;
      }
      if (file.size > MAX_FILE_BYTES) {
        this.form.document = null;
        this.errors.document = 'File must be 5 MB or smaller.';
        return;
      }

      this.form.document = file;
      this.errors.document = '';
    },

    /* ---------------- navigation ---------------- */

    goToStep(target) {
      if (target === 2) {
        // Run all three, then check — so every error shows at once.
        const checks = [
          this.validateName(),
          this.validateIdNumber(),
          this.validateDateOfBirth(),
        ];
        if (!checks.every(Boolean)) return;
      }

      if (target === 3) {
        const checks = [this.validateIncome(), this.validateDocument()];
        if (!checks.every(Boolean)) return;
        this.fetchPhones();
      }

      if (target === 4 && !this.form.phoneId) return;

      this.step = target;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    /* ---------------- server calls ---------------- */

    async fetchPhones() {
      this.loadingPhones = true;
      this.serverError = '';
      this.phones = [];

      try {
        const income = encodeURIComponent(this.form.monthlyIncome);
        const response = await fetch(`/api/phones?monthly_income=${income}`);
        if (!response.ok) throw new Error('Could not load phones.');

        this.phones = await response.json();

        // If their previous pick is no longer affordable, clear it.
        if (!this.phones.some((p) => p.id === this.form.phoneId)) {
          this.form.phoneId = null;
        }
      } catch (error) {
        this.serverError = error.message;
      } finally {
        this.loadingPhones = false;
      }
    },

    async submit() {
      this.serverError = '';
      this.submitting = true;

      try {
        const body = new FormData();
        body.append('full_name', this.form.fullName);
        body.append('id_number', this.form.idNumber);
        body.append('date_of_birth', this.form.dateOfBirth);
        body.append('monthly_income', this.form.monthlyIncome);
        body.append('phone_id', this.form.phoneId);
        body.append('document', this.form.document);

        // Deliberately no Content-Type header — see notes.
        const response = await fetch('/api/applications', { method: 'POST', body });
        const payload = await response.json().catch(() => ({}));

        if (!response.ok) {
          this.serverError = readError(payload, response.status);
          return;
        }

        this.result = payload;
        this.submitted = true;
        window.scrollTo({ top: 0 });
      } catch (error) {
        this.serverError = 'Could not reach the server. Check your connection.';
      } finally {
        this.submitting = false;
      }
    },

    startOver() {
      Object.assign(this.$data, this.$options.data());
    },

    /* ---------------- display helpers ---------------- */

    humanSize(bytes) {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    },

    percent(fraction) {
      return `${Math.round(Number(fraction) * 100)}%`;
    },

    brandColour(brand) {
      const palette = ['#C2410C', '#0F766E', '#1D4ED8', '#7E22CE', '#B45309', '#15803D'];
      let hash = 0;
      for (const char of brand) hash = (hash + char.charCodeAt(0)) % palette.length;
      return palette[hash];
    },
  },
}).mount('#app');