# DCC input power sensors

DCC entries include **Combined Input Power** in the **Status** group, measured
in watts. With renogy-ble 2.12.2, numeric readings are supported only for the
verified **RBC50D1S-G7** model (case and surrounding whitespace are ignored).
Other DCC models retain their existing power interpretation and the combined
input sensor remains unknown when the library does not supply that field.

On RBC50D1S-G7, Combined Input Power reports the total solar and alternator
input. Alternator Power retains its reported value; Solar Power reports the
solar contribution calculated by the library. Existing Solar Power and
Alternator Power entity IDs are preserved. For example, 93 W combined and
74 W alternator input yield 19 W solar input.

Use the separate solar contribution when measuring solar generation; combined
input includes alternator power too. Do not add the combined value to its
individual inputs when calculating total input power.

Protocol interpretation and model support belong to renogy-ble. The scope and
captured-frame evidence are recorded in
[renogy-ble PR #207](https://github.com/IAmTheMitchell/renogy-ble/pull/207) and
[renogy-ha issue #150](https://github.com/IAmTheMitchell/renogy-ha/issues/150).
