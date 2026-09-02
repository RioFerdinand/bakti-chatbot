import "./logout.css";

export default function LogoutModal({
    onCancel,
    onConfirm
}){

    return(

        <div className="logout-wrapper">

            <div className="logout-box">

                <h2>
                    Keluar dari BAKTI Assistant?
                </h2>

                <div className="logout-action">

                    <button
                        className="cancel"
                        onClick={onCancel}
                    >
                        Batal
                    </button>

                    <button
                    className="logout"
                    onClick={onConfirm}
                    >
                    Keluar
                    </button>

                </div>

            </div>

        </div>

    )

}