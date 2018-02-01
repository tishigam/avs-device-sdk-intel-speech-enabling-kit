/**
 * AlsaHardwareController.h
 *
 * TODO: Add Intel copyright
 */

#ifndef ALEXA_CLIENT_SDK_KWD_ALSA_HW_CTRL_H_
#define ALEXA_CLIENT_SDK_KWD_ALSA_HW_CTRL_H_

#include <chrono>
#include <string>
#include <memory>

#include <alsa/asoundlib.h>

#include "HardwareController/AbstractHardwareController.h"

namespace alexaClientSDK {
namespace kwd {

class AlsaHardwareController : public AbstractHardwareController {
public:
    /**
     * Creates a new pointer to an @c AlsaHardwareController.
     *
     * @param name Name of the ALSA device to connect to, ex. "hw:0"
     * @param keyword Keyword which will be detected from the ALSA control device
     * @return @c AlsaHardwareController, nullptr otherwise
     */
    static std::shared_ptr<AlsaHardwareController> create(std::string name, std::string keyword);

    /**
     * Read a @c KeywordDetection from the hardware controller.
     *
     * @param timeout Timeout for the read
     * @return @c KeywordDetection when a detection occurs, otherwise @c nullptr
     * if an error occurs, or a timeout
     */
    std::unique_ptr<KeywordDetection> read(std::chrono::milliseconds timout) override;
    
    /**
     * Destructor.
     */
    ~AlsaHardwareController();

private:
    /**
     * Constructor.
     *
     * @param name Name of the ALSA device to connect to
     * @param keyword Keyword which will be detected from the ALSA control device
     */
    AlsaHardwareController(std::string name, std::string keyword);

    /**
     * Initialize the connection to the ALSA driver.
     *
     * @return @c true if init succeeds, @c false otherwise
     */
    bool init();

    /// Name of the ALSA controller to connect to
    std::string m_name;

    /// Keyword which is detected by the ALSA control device
    std::string m_keyword;

    /// Handle to the ALSA control device
    snd_ctl_t* m_ctl;
};

} // kwd
} // alexaClientSDK

#endif // ALEXA_CLIENT_SDK_KWD_ALSA_HW_CTRL_H_
