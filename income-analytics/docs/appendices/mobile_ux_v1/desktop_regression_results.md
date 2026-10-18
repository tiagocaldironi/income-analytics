# Desktop regression

Automated Chrome viewport: **1440×900**. The desktop primary navigation computed to `display:flex`, mobile bottom navigation to `display:none`, and the document remained 1440 px wide. The existing dashboard and grouped holdings table render from the same DOM and API responses as mobile. A screenshot is saved at `screenshots/desktop-1440x900/dashboard.png`.

Displayed value comparison at 390×844 and 1440×900 matched exactly for portfolio equity and first holding identity/quote text. The exact value and identity are omitted from this report because the repository is public. No backend or financial calculation code changed. Desktop values were not recomputed or transformed by the responsive CSS.
