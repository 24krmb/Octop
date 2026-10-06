import { Button, Modal } from "antd";
import { useTranslation } from "react-i18next";

import styles from "./ForgotPasswordModal.module.less";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function ForgotPasswordModal({ open, onClose }: Props) {
  const { t } = useTranslation();

  return (
    <Modal
      open={open}
      title={t("login.forgotPasswordTitle", "Reset password")}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={onClose}>
          {t("login.forgotPasswordOk", "Got it")}
        </Button>
      }
      width={420}
      centered
      destroyOnHidden
    >
      <div className={styles.body} data-testid="login-forgot-password">
        <p className={styles.help}>
          请联系管理员「qhxn004@foxmail.com」重置。
        </p>
      </div>
    </Modal>
  );
}
